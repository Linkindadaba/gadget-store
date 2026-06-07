import hmac
from abc import ABC, abstractmethod
import hashlib
import json
import uuid
from decimal import Decimal

import requests
from django.conf import settings
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django_ratelimit.decorators import ratelimit

from orders.models import Order
from .models import Payment
import logging

logger = logging.getLogger(__name__)

# Expected header names for webhooks
PAYSTACK_WEBHOOK_SECRET_HEADER = 'x-paystack-signature'
FLUTTERWAVE_WEBHOOK_SECRET_HEADER = 'verif-hash'

def _paystack_headers():
    return {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }


def _flutterwave_headers(secret_key=None):
    key = secret_key or settings.FLUTTERWAVE_SECRET_KEY
    return {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }

class PaymentGatewayError(Exception):
    pass

class BasePaymentGateway(ABC):
    @abstractmethod
    def generate_link(self, request, order, payment, **kwargs):
        pass

    @abstractmethod
    def verify(self, payment, transaction_id=None):
        pass

    @abstractmethod
    def validate_webhook(self, request):
        pass

class FlutterwaveGateway(BasePaymentGateway):
    BASE_URL = "https://api.flutterwave.com/v3"

    def _get_headers(self):
        return {
            'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
            'Content-Type': 'application/json',
        }

    def generate_link(self, request, order, payment, **kwargs):
        payload = {
            "tx_ref": payment.reference,
            "amount": str(payment.amount),
            "currency": settings.FLUTTERWAVE_CURRENCY,
            "redirect_url": request.build_absolute_uri(reverse('payments:payment_callback')),
            "customer": {
                "email": order.email,
                "phonenumber": kwargs.get('phone_number', ""),
                "name": f"{order.first_name} {order.last_name}",
            },
        }
        try:
            resp = requests.post(f"{self.BASE_URL}/payments", json=payload, headers=self._get_headers(), timeout=20)
            data = resp.json()
            if resp.status_code >= 400 or data.get('status') != 'success':
                raise PaymentGatewayError(data.get('message', 'Flutterwave error'))
            return data.get('data', {}).get('link')
        except requests.exceptions.RequestException:
            raise PaymentGatewayError("Flutterwave connection failed")

    def verify(self, payment, transaction_id=None):
        tid = transaction_id or payment.gateway_transaction_id
        if not tid: raise PaymentGatewayError("No transaction ID")
        url = f"{self.BASE_URL}/transactions/{tid}/verify"
        resp = requests.get(url, headers=self._get_headers(), timeout=15)
        return resp.json().get('data')

    def validate_webhook(self, request):
        sent_hash = request.headers.get('verif-hash')
        return sent_hash and hmac.compare_digest(sent_hash, settings.FLUTTERWAVE_WEBHOOK_SECRET)

class PaystackGateway(BasePaymentGateway):
    BASE_URL = "https://api.paystack.co"

    def _get_headers(self):
        return {
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        }

    def generate_link(self, request, order, payment, **kwargs):
        # Validate secret key early to provide a clear error message instead of
        # allowing Paystack to respond with an opaque "invalid key" error.
        sk = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
        if not sk or sk.strip() == '' or 'xxxx' in sk:
            logger.error("Paystack API call attempted but Secret Key is missing or using placeholder.")
            raise PaymentGatewayError('Paystack secret key not configured. Set PAYSTACK_SECRET_KEY in environment.')

        payload = {
            "email": order.email,
            "amount": int(payment.amount * 100),
            "currency": settings.PAYSTACK_CURRENCY,
            "reference": payment.reference,
            "callback_url": request.build_absolute_uri(reverse('payments:payment_callback')),
        }
        try:
            logger.info(f"Initializing Paystack transaction for Order {order.order_number}")
            resp = requests.post(f"{self.BASE_URL}/transaction/initialize", json=payload, headers=self._get_headers(), timeout=20)
            data = resp.json()
            if resp.status_code >= 400 or not data.get('status'):
                raise PaymentGatewayError(f"Paystack Error: {data.get('message', 'Unknown Error')}")
            return data.get('data', {}).get('authorization_url')
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack connection error: {e}")
            raise PaymentGatewayError("Could not connect to Paystack. Please check your internet or try again later.")

    def verify(self, payment, transaction_id=None):
        sk = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
        if not sk or sk.strip() == '' or 'xxxx' in sk:
            raise PaymentGatewayError('Paystack secret key not configured. Set PAYSTACK_SECRET_KEY in environment.')

        url = f"{self.BASE_URL}/transaction/verify/{payment.reference}"
        resp = requests.get(url, headers=self._get_headers(), timeout=15)
        return resp.json().get('data')

    def validate_webhook(self, request):
        signature = request.headers.get('x-paystack-signature')
        if not signature: return False
        expected = hmac.new(settings.PAYSTACK_WEBHOOK_SECRET.encode('utf-8'), request.body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(signature, expected)

GATEWAYS = {
    'flutterwave': FlutterwaveGateway(),
    'paystack': PaystackGateway(),
}

def _get_gateway_strategy(payment_or_name):
    name = payment_or_name if isinstance(payment_or_name, str) else _get_payment_gateway(payment_or_name)
    return GATEWAYS.get(name)


def _payment_amount_matches(received_amount, expected_amount):
    try:
        return Decimal(str(received_amount)).quantize(Decimal('0.01')) == expected_amount.quantize(Decimal('0.01'))
    except Exception:
        return False


def _get_payment_gateway(payment):
    if hasattr(payment, 'gateway') and payment.gateway:
        return payment.gateway

    if payment.reference and payment.reference.startswith('PAY-'):
        return 'paystack'

    return 'flutterwave'


def _mark_payment_from_charge(payment, charge, gateway=None):
    gateway = gateway or _get_payment_gateway(payment)
    payment.gateway_response = json.dumps(charge)
    payment.gateway_transaction_id = str(charge.get('id') or charge.get('reference') or payment.gateway_transaction_id)

    reference = charge.get('tx_ref') or charge.get('reference')
    status = charge.get('status')
    currency = charge.get('currency')
    amount = charge.get('amount')

    if gateway == 'paystack' and amount is not None:
        try:
            amount = Decimal(str(amount)) / Decimal('100')
        except Exception:
            amount = None

    expected_currency = settings.PAYSTACK_CURRENCY if gateway == 'paystack' else settings.FLUTTERWAVE_CURRENCY
    success_states = ['successful', 'succeeded', 'success']

    if (
        reference == payment.reference
        and status in success_states
        and currency == expected_currency
        and _payment_amount_matches(amount, payment.amount)
    ):
        order = payment.order
        if order.status != 'paid':
            order.status = 'paid'
            order.save(update_fields=['status'])
            
            # Reduce stock now that payment is confirmed
            for item in order.items.all():
                if item.product:
                    item.product.stock = max(0, item.product.stock - item.quantity)
                    item.product.save(update_fields=['stock'])

        payment.status = 'success'
        payment.paid_at = timezone.now()
        payment.save(update_fields=['status', 'paid_at', 'gateway_transaction_id', 'gateway_response'])
        return True

    payment.status = 'failed' if status in ['failed', 'cancelled'] else 'pending'
    payment.save(update_fields=['status', 'gateway_transaction_id', 'gateway_response'])
    return False


@require_http_methods(['GET', 'POST'])
@ratelimit(key='ip', rate='200/h', block=True)
def initiate_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, status='pending')

    for item in order.items.all():
        if item.product and item.quantity > item.product.stock:
            messages.error(request, f"Transaction aborted: {item.product.name} is now out of stock.")
            return redirect('store:cart')

    selected_gateway = request.POST.get('gateway') if request.method == 'POST' else None
    if selected_gateway not in ['flutterwave', 'paystack']:
        selected_gateway = None

    calculated_total = order.get_total_amount()
    gateway_prefix = 'FLW' if (selected_gateway or 'flutterwave') == 'flutterwave' else 'PAY'
    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            'amount': calculated_total,
            'reference': f"{gateway_prefix}-{order.order_number}-{uuid.uuid4().hex[:8]}",
            'status': 'pending',
            'gateway': selected_gateway or 'flutterwave',
        }
    )

    if not selected_gateway:
        selected_gateway = payment.gateway or 'flutterwave'

    if not created and payment.gateway != selected_gateway:
        payment.gateway = selected_gateway
        gateway_prefix = 'FLW' if selected_gateway == 'flutterwave' else 'PAY'
        payment.reference = f"{gateway_prefix}-{order.order_number}-{uuid.uuid4().hex[:8]}"
        payment.gateway_transaction_id = ''
        payment.gateway_response = ''
        payment.status = 'pending'
        payment.amount = calculated_total
        payment.save(update_fields=['gateway', 'reference', 'gateway_transaction_id', 'gateway_response', 'status', 'amount'])

    if payment.amount != calculated_total:
        payment.amount = calculated_total
        payment.save(update_fields=['amount'])

    if request.method == 'POST':
        try:
            strategy = _get_gateway_strategy(selected_gateway)
            if not strategy:
                messages.error(request, "Invalid payment gateway selected.")
                return redirect('payments:initiate', order_id=order.id)

            gateway_kwargs = {}
            if selected_gateway == 'flutterwave':
                network = request.POST.get('network')
                phone_number = request.POST.get('phone_number')
                if not network or not phone_number:
                    messages.error(request, 'Please select a network and provide a valid phone number for Flutterwave.')
                    return redirect('payments:initiate', order_id=order.id)
                gateway_kwargs.update({'network': network, 'phone_number': phone_number})

            payment_link = strategy.generate_link(request, order, payment, **gateway_kwargs)
            return redirect(payment_link)
            
        except PaymentGatewayError as e:
            messages.error(request, str(e))
            return redirect('store:cart')

    return render(request, 'payments/initiate.html', {
        'order': order,
        'payment': payment,
        'currency': settings.FLUTTERWAVE_CURRENCY,
        'gateways': [
            ('flutterwave', 'Flutterwave (Mobile Money)'),
            ('paystack', 'Paystack (Card, Mobile Money, USSD)'),
        ],
        'networks': settings.FLUTTERWAVE_MOBILE_MONEY_NETWORKS,
        'selected_gateway': selected_gateway,
    })


@csrf_exempt
@require_http_methods(['POST'])
@ratelimit(key='ip', rate='1000/h', block=True)
def payment_webhook(request):
    if request.headers.get(PAYSTACK_WEBHOOK_SECRET_HEADER):
        return _handle_paystack_webhook(request)

    if request.headers.get(FLUTTERWAVE_WEBHOOK_SECRET_HEADER):
        return _handle_flutterwave_webhook(request)

    logger.warning('Payment Webhook: No known gateway signature header found.')
    return HttpResponseBadRequest('No valid webhook signature header found.')


def _handle_flutterwave_webhook(request):
    secret_hash = settings.FLUTTERWAVE_WEBHOOK_SECRET
    if not secret_hash:
        logger.error("Flutterwave Webhook: Secret hash not configured in settings. This is a critical security issue.")
        return HttpResponseBadRequest("Webhook secret not configured on server.")

    flw_hash = request.headers.get(FLUTTERWAVE_WEBHOOK_SECRET_HEADER)
    if not flw_hash:
        logger.warning("Flutterwave Webhook: No 'verif-hash' header found in the request.")
        return HttpResponseBadRequest("No Flutterwave hash in header.")

    if not hmac.compare_digest(flw_hash.encode('utf-8'), secret_hash.encode('utf-8')):
        logger.warning("Flutterwave Webhook: Invalid 'verif-hash' received. Possible unauthorized request.")
        return HttpResponseBadRequest("Invalid Flutterwave hash.")

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("Flutterwave Webhook: Invalid JSON payload received.")
        return HttpResponseBadRequest("Invalid JSON payload.")

    event_type = payload.get('event')
    charge_data = payload.get('data', {})
    logger.info(f"Flutterwave Webhook received: Event={event_type}, Data={charge_data}")

    if event_type == 'charge.completed':
        reference = charge_data.get('tx_ref')
        if not reference:
            logger.error("Flutterwave Webhook: 'tx_ref' missing from charge.completed event payload.")
            return JsonResponse({"status": "error", "message": "Missing transaction reference"}, status=400)

        try:
            payment = Payment.objects.get(reference=reference)
            _mark_payment_from_charge(payment, charge_data, gateway='flutterwave')
            logger.info(f"Payment for order {payment.order.order_number} (Ref: {reference}) processed via webhook. Status: {payment.status}")
        except Payment.DoesNotExist:
            logger.error(f"Flutterwave Webhook: Payment with reference {reference} not found in database.")
        except Exception as e:
            logger.exception(f"Flutterwave Webhook: Error processing charge.completed event for reference {reference}: {e}")
    else:
        logger.info(f"Flutterwave Webhook: Unhandled event type: {event_type}. No action taken.")

    return JsonResponse({"status": "success"})


def _handle_paystack_webhook(request):
    secret = settings.PAYSTACK_WEBHOOK_SECRET
    if not secret:
        logger.error("Paystack Webhook: Secret not configured in settings.")
        return HttpResponseBadRequest("Webhook secret not configured on server.")

    remote_addr = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    if ',' in remote_addr:
        remote_addr = remote_addr.split(',')[0].strip()

    allowed_ips = getattr(settings, 'PAYSTACK_ALLOWED_IPS', [])
    if allowed_ips and remote_addr and remote_addr not in allowed_ips:
        logger.warning(f"Paystack Webhook: Request from disallowed IP {remote_addr}")
        return HttpResponseBadRequest("Webhook source IP not allowed.")

    signature = request.headers.get(PAYSTACK_WEBHOOK_SECRET_HEADER)
    if not signature:
        logger.warning("Paystack Webhook: Missing signature header.")
        return HttpResponseBadRequest("Missing Paystack signature.")

    expected_signature = hmac.new(secret.encode('utf-8'), request.body, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        logger.warning("Paystack Webhook: Invalid signature received.")
        return HttpResponseBadRequest("Invalid Paystack signature.")

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("Paystack Webhook: Invalid JSON payload received.")
        return HttpResponseBadRequest("Invalid JSON payload.")

    event_type = payload.get('event')
    data = payload.get('data', {})
    logger.info(f"Paystack Webhook received: Event={event_type}, Data={data}")

    if event_type in ['charge.success', 'transaction.success'] or data.get('status') == 'success':
        reference = data.get('reference')
        if not reference:
            logger.error("Paystack Webhook: Missing 'reference' in payload.")
            return JsonResponse({"status": "error", "message": "Missing transaction reference"}, status=400)

        try:
            payment = Payment.objects.get(reference=reference)
            _mark_payment_from_charge(payment, data, gateway='paystack')
            logger.info(f"Payment for order {payment.order.order_number} (Ref: {reference}) processed via webhook. Status: {payment.status}")
        except Payment.DoesNotExist:
            logger.error(f"Paystack Webhook: Payment with reference {reference} not found in database.")
        except Exception as e:
            logger.exception(f"Paystack Webhook: Error processing Paystack webhook for reference {reference}: {e}")
    else:
        logger.info(f"Paystack Webhook: Unhandled event type: {event_type}. No action taken.")

    return JsonResponse({"status": "success"})


def _process_verification(payment, transaction_id=None):
    """Unified logic to verify and process a payment from any gateway."""
    strategy = _get_gateway_strategy(payment)
    try:
        charge_data = strategy.verify(payment, transaction_id=transaction_id)
        return _mark_payment_from_charge(payment, charge_data, gateway=payment.gateway)
    except Exception as e:
        logger.error(f"Verification Failed for {payment.reference}: {e}")
        return False


@require_http_methods(['GET'])
def verify_payment(request, reference):
    payment = get_object_or_404(Payment, reference=reference)
    if _process_verification(payment):
        return render(request, 'payments/success.html', {'order': payment.order})
    return render(request, 'payments/failure.html', {'order': payment.order})


def payment_callback(request):
    reference = request.GET.get('reference') or request.GET.get('tx_ref') or request.GET.get('trxref')
    if reference:
        payment = get_object_or_404(Payment, reference=reference)
        if _process_verification(payment, transaction_id=request.GET.get('transaction_id')):
            return render(request, 'payments/success.html', {'order': payment.order})
    
    if not reference: return redirect('store:home')
    return render(request, 'payments/failure.html', {'order': payment.order})
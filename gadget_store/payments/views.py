import hmac
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

from orders.models import Order
from .models import Payment
import logging

logger = logging.getLogger(__name__)

FLW_PAYMENT_URL = "https://api.flutterwave.com/v3/payments"
PAYSTACK_BASE_URL = "https://api.paystack.co"
PAYSTACK_INIT_URL = f"{PAYSTACK_BASE_URL}/transaction/initialize"
PAYSTACK_VERIFY_URL = f"{PAYSTACK_BASE_URL}/transaction/verify"
FLUTTERWAVE_WEBHOOK_SECRET_HEADER = 'verif-hash'
PAYSTACK_WEBHOOK_SECRET_HEADER = 'x-paystack-signature'


class PaymentGatewayError(Exception):
    pass


def _flutterwave_headers(token, trace_id=None, idempotency_key=None):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'X-Trace-Id': trace_id or str(uuid.uuid4()),
    }
    if idempotency_key:
        headers['X-Idempotency-Key'] = idempotency_key
    return headers


def _paystack_headers():
    return {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }


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

        payment.status = 'success'
        payment.paid_at = timezone.now()
        payment.save(update_fields=['status', 'paid_at', 'gateway_transaction_id', 'gateway_response'])
        return True

    payment.status = 'failed' if status in ['failed', 'cancelled'] else 'pending'
    payment.save(update_fields=['status', 'gateway_transaction_id', 'gateway_response'])
    return False


def _generate_flutterwave_link(request, order, payment, network=None, phone_number=None):
    payload = {
        "tx_ref": payment.reference,
        "amount": str(order.get_total_amount()),
        "currency": settings.FLUTTERWAVE_CURRENCY,
        "redirect_url": request.build_absolute_uri(reverse('payments:payment_callback')),
        "customer": {
            "email": order.email,
            "phonenumber": phone_number or getattr(order, 'phone', ""),
            "name": f"{order.first_name} {order.last_name}",
        },
        "customizations": {
            "title": "F.B Nation Gadget Store",
            "description": f"Payment for Order {order.order_number}",
        },
    }

    headers = _flutterwave_headers(settings.FLUTTERWAVE_SECRET_KEY)

    try:
        response = requests.post(FLW_PAYMENT_URL, json=payload, headers=headers, timeout=20)
        data = response.json()

        if response.status_code >= 400 or data.get('status') != 'success':
            logger.error(f"Flutterwave Link Error: {data}")
            raise PaymentGatewayError(data.get('message', 'Could not generate payment link.'))

        return data.get('data', {}).get('link')
    except requests.exceptions.RequestException as e:
        logger.error(f"Flutterwave Request Exception: {e}")
        raise PaymentGatewayError("Communication error with Flutterwave.")


def _generate_paystack_link(request, order, payment):
    payload = {
        "email": order.email,
        "amount": int(order.get_total_amount() * 100),
        "currency": settings.PAYSTACK_CURRENCY,
        "reference": payment.reference,
        "callback_url": request.build_absolute_uri(reverse('payments:payment_callback')),
        "metadata": {
            "order_number": order.order_number,
        },
    }

    headers = _paystack_headers()

    try:
        response = requests.post(PAYSTACK_INIT_URL, json=payload, headers=headers, timeout=20)
        data = response.json()

        if response.status_code >= 400 or not data.get('status'):
            logger.error(f"Paystack Init Error: {data}")
            raise PaymentGatewayError(data.get('message', 'Could not initialize Paystack payment.'))

        return data.get('data', {}).get('authorization_url')
    except requests.exceptions.RequestException as e:
        logger.error(f"Paystack Request Exception: {e}")
        raise PaymentGatewayError("Communication error with Paystack.")


def _verify_paystack_transaction(reference):
    url = f"{PAYSTACK_VERIFY_URL}/{reference}"
    headers = _paystack_headers()

    response = requests.get(url, headers=headers, timeout=15)
    data = response.json()

    if response.status_code >= 400 or not data.get('status'):
        raise PaymentGatewayError(data.get('message', 'Could not verify Paystack transaction.'))

    return data.get('data', {})


@require_http_methods(['GET', 'POST'])
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
            if selected_gateway == 'paystack':
                payment_link = _generate_paystack_link(request, order, payment)
            else:
                network = request.POST.get('network')
                phone_number = request.POST.get('phone_number')
                if not network or not phone_number:
                    messages.error(request, 'Please select a network and provide a valid Ghana phone number for Flutterwave payments.')
                    return redirect('payments:initiate', order_id=order.id)
                payment_link = _generate_flutterwave_link(request, order, payment, network=network, phone_number=phone_number)

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


@require_http_methods(['GET'])
def verify_payment(request, reference):
    payment = get_object_or_404(Payment, reference=reference)
    gateway = _get_payment_gateway(payment)

    try:
        if gateway == 'flutterwave':
            if not payment.gateway_transaction_id:
                raise PaymentGatewayError('No Flutterwave transaction ID is available for manual verification.')

            verify_url = f"https://api.flutterwave.com/v3/transactions/{payment.gateway_transaction_id}/verify"
            headers = _flutterwave_headers(settings.FLUTTERWAVE_SECRET_KEY)
            response = requests.get(verify_url, headers=headers, timeout=15)
            data = response.json()
            if data.get('status') == 'success' and _mark_payment_from_charge(payment, data.get('data'), gateway='flutterwave'):
                return render(request, 'payments/success.html', {'order': payment.order})

        else:
            paystack_data = _verify_paystack_transaction(payment.reference)
            if _mark_payment_from_charge(payment, paystack_data, gateway='paystack'):
                return render(request, 'payments/success.html', {'order': payment.order})
    except Exception as e:
        logger.error(f"Error verifying payment {reference}: {e}")

    return render(request, 'payments/failure.html', {'order': payment.order})


def payment_callback(request):
    reference = request.GET.get('reference') or request.GET.get('tx_ref') or request.GET.get('trxref')
    transaction_id = request.GET.get('transaction_id')

    if not reference:
        logger.warning(f"Callback accessed without required reference. reference: {reference}")
        return redirect('store:home')

    payment = get_object_or_404(Payment, reference=reference)
    gateway = _get_payment_gateway(payment)

    try:
        if gateway == 'flutterwave':
            if not transaction_id:
                raise PaymentGatewayError('Missing Flutterwave transaction ID on callback.')

            verify_url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
            headers = _flutterwave_headers(settings.FLUTTERWAVE_SECRET_KEY)
            response = requests.get(verify_url, headers=headers, timeout=15)
            data = response.json()
            if data.get('status') == 'success' and _mark_payment_from_charge(payment, data.get('data'), gateway='flutterwave'):
                return render(request, 'payments/success.html', {'order': payment.order})

        else:
            paystack_data = _verify_paystack_transaction(payment.reference)
            if _mark_payment_from_charge(payment, paystack_data, gateway='paystack'):
                return render(request, 'payments/success.html', {'order': payment.order})
    except Exception as e:
        logger.error(f"Error verifying payment {reference}: {e}")

    return render(request, 'payments/failure.html', {'order': payment.order})
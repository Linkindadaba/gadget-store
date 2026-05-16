import hmac
import hashlib
import json
import uuid
from decimal import Decimal

import requests
from django.conf import settings
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from orders.models import Order
from .models import Payment
import logging


logger = logging.getLogger(__name__)

MOBILE_MONEY_NETWORKS = [
    ('MTN', 'MTN Mobile Money'),
    ('VODAFONE', 'Telecel Cash'),
    ('AIRTELTIGO', 'AirtelTigo Money'),
]

FLW_CHARGE_URL = "https://api.flutterwave.com/v3/charges?type=mobile_money_ghana"


class FlutterwaveError(Exception):
    pass

FLUTTERWAVE_WEBHOOK_SECRET_HEADER = 'verif-hash'


def _flutterwave_headers(token, trace_id=None, idempotency_key=None):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'X-Trace-Id': trace_id or str(uuid.uuid4()),
    }
    if idempotency_key:
        headers['X-Idempotency-Key'] = idempotency_key
    return headers


def _payment_amount_matches(received_amount, expected_amount):
    try:
        return Decimal(str(received_amount)).quantize(Decimal('0.01')) == expected_amount.quantize(Decimal('0.01'))
    except Exception:
        return False


def _mark_payment_from_charge(payment, charge):
    payment.gateway_response = json.dumps(charge)
    payment.gateway_transaction_id = charge.get('id') or payment.gateway_transaction_id
    
    if (
        (charge.get('tx_ref') == payment.reference or charge.get('reference') == payment.reference)
        and charge.get('status') in ['successful', 'succeeded']
        and charge.get('currency') == settings.FLUTTERWAVE_CURRENCY
        and _payment_amount_matches(charge.get('amount'), payment.amount)
    ):
        payment.status = 'success'
        payment.paid_at = timezone.now()
        payment.save()
        
        order = payment.order
        order.status = 'paid'
        order.save()
        return True

    payment.status = 'failed' if charge.get('status') in ['failed', 'cancelled'] else 'pending'
    payment.save()
    return False


def _create_mobile_money_charge(request, order, payment, network, phone_number):
    payload = {
        "amount": str(payment.amount),
        "currency": settings.FLUTTERWAVE_CURRENCY,
        "email": order.email,
        "tx_ref": payment.reference,
        "phone_number": phone_number,
        "network": network,
        "fullname": f"{order.first_name} {order.last_name}",
        "redirect_url": request.build_absolute_uri(reverse('payments:payment_callback')),
    }
    
    headers = _flutterwave_headers(settings.FLUTTERWAVE_SECRET_KEY, idempotency_key=payment.reference)
    
    try:
        response = requests.post(FLW_CHARGE_URL, json=payload, headers=headers, timeout=20)
        data = response.json()
        
        if response.status_code >= 400:
            logger.error(f"Flutterwave Charge Error: {data}")
            raise FlutterwaveError(data.get('message', 'Could not initiate mobile money charge.'))
            
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Flutterwave Request Exception: {e}")
        raise FlutterwaveError("Communication error with Flutterwave.")


@require_http_methods(['GET', 'POST'])
def initiate_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, status='pending')
    
    # Calculate total price manually to resolve AttributeError if total_price is missing on Order model
    items_total = sum(item.price * item.quantity for item in order.items.all())
    delivery_fee = order.delivery_zone.fee if order.delivery_zone else Decimal('0.00')
    calculated_total = items_total + delivery_fee

    # Create or retrieve the payment record
    payment, _ = Payment.objects.get_or_create(
        order=order,
        defaults={
            'amount': calculated_total,
            'reference': f"FLW-{order.order_number}-{uuid.uuid4().hex[:8]}",
            'status': 'pending'
        }
    )

    if request.method == 'POST':
        network = request.POST.get('network')
        phone_number = request.POST.get('phone_number')
        
        if not network or not phone_number:
            return render(request, 'payments/initiate.html', {
                'order': order,
                'payment': payment,
                'currency': settings.FLUTTERWAVE_CURRENCY,
                'networks': MOBILE_MONEY_NETWORKS,
                'error': 'Please provide both network and phone number.'
            })
            
        try:
            charge_response = _create_mobile_money_charge(request, order, payment, network, phone_number)
            payment.gateway_transaction_id = charge_response.get('data', {}).get('id')
            payment.save()
            
            return render(request, 'payments/processing.html', {
                'order': order,
                'message': charge_response.get('message', 'A prompt has been sent to your phone. Please approve to complete payment.')
            })
        except FlutterwaveError as e:
            return render(request, 'payments/initiate.html', {
                'order': order,
                'payment': payment,
                'currency': settings.FLUTTERWAVE_CURRENCY,
                'networks': MOBILE_MONEY_NETWORKS,
                'error': str(e)
            })

    return render(request, 'payments/initiate.html', {
        'order': order,
        'payment': payment,
        'currency': settings.FLUTTERWAVE_CURRENCY,
        'networks': MOBILE_MONEY_NETWORKS
    })


@csrf_exempt
@require_http_methods(['POST'])
def flutterwave_webhook(request):
    # 1. Get the secret hash from settings
    secret_hash = settings.FLUTTERWAVE_WEBHOOK_SECRET
    if not secret_hash:
        logger.error("Flutterwave Webhook: Secret hash not configured in settings. This is a critical security issue.")
        return HttpResponseBadRequest("Webhook secret not configured on server.")

    # 2. Get the hash from the request header
    flw_hash = request.headers.get(FLUTTERWAVE_WEBHOOK_SECRET_HEADER)

    if not flw_hash:
        logger.warning("Flutterwave Webhook: No 'verif-hash' header found in the request.")
        return HttpResponseBadRequest("No Flutterwave hash in header.")

    # 3. Compare the hashes securely
    # Note: hmac.compare_digest expects bytes, so encode both strings
    if not hmac.compare_digest(flw_hash.encode('utf-8'), secret_hash.encode('utf-8')):
        logger.warning("Flutterwave Webhook: Invalid 'verif-hash' received. Possible unauthorized request.")
        return HttpResponseBadRequest("Invalid Flutterwave hash.")

    # 4. Process the payload
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("Flutterwave Webhook: Invalid JSON payload received.")
        return HttpResponseBadRequest("Invalid JSON payload.")

    event_type = payload.get('event')
    charge_data = payload.get('data', {}) # This is the 'charge' object from Flutterwave

    logger.info(f"Flutterwave Webhook received: Event={event_type}, Data={charge_data}")

    if event_type == 'charge.completed':
        reference = charge_data.get('tx_ref')
        if not reference:
            logger.error("Flutterwave Webhook: 'tx_ref' missing from charge.completed event payload.")
            return JsonResponse({"status": "error", "message": "Missing transaction reference"}, status=400)

        try:
            payment = Payment.objects.get(reference=reference)
            # Use the existing _mark_payment_from_charge function to update payment and order status
            _mark_payment_from_charge(payment, charge_data)
            logger.info(f"Payment for order {payment.order.order_number} (Ref: {reference}) processed via webhook. Status: {payment.status}")
        except Payment.DoesNotExist:
            logger.error(f"Flutterwave Webhook: Payment with reference {reference} not found in database.")
        except Exception as e:
            logger.exception(f"Flutterwave Webhook: Error processing charge.completed event for reference {reference}: {e}")
    else:
        logger.info(f"Flutterwave Webhook: Unhandled event type: {event_type}. No action taken.")

    # Always return 200 OK to Flutterwave to acknowledge receipt, even if processing failed internally.
    return JsonResponse({"status": "success"})


def payment_callback(request):
    """Handle the redirect from Flutterwave after a payment attempt."""
    tx_ref = request.GET.get('tx_ref')
    transaction_id = request.GET.get('transaction_id')
    
    if not tx_ref or not transaction_id:
        logger.warning(f"Callback accessed without required parameters. tx_ref: {tx_ref}, transaction_id: {transaction_id}")
        return redirect('store:home')
        
    payment = get_object_or_404(Payment, reference=tx_ref)
    
    try:
        verify_url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
        headers = _flutterwave_headers(settings.FLUTTERWAVE_SECRET_KEY)
        
        response = requests.get(verify_url, headers=headers, timeout=15)
        data = response.json()
        
        if data.get('status') == 'success':
            if _mark_payment_from_charge(payment, data.get('data')):
                return render(request, 'payments/success.html', {'order': payment.order})
    except Exception as e:
        logger.error(f"Error verifying payment {tx_ref}: {e}")

    return render(request, 'payments/failure.html', {'order': payment.order})
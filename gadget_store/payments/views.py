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


def _get_flutterwave_token():
    if not settings.FLUTTERWAVE_CLIENT_ID or not settings.FLUTTERWAVE_CLIENT_SECRET:
        raise FlutterwaveError('Flutterwave credentials are not configured.')
    
    response = requests.post(
        settings.FLUTTERWAVE_AUTH_URL,
        data={
            'client_id': settings.FLUTTERWAVE_CLIENT_ID,
            'client_secret': settings.FLUTTERWAVE_CLIENT_SECRET,
            'grant_type': 'client_credentials',
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=15,
    )
    data = response.json() # type: ignore
    token = data.get('access_token')
    if response.status_code >= 400 or not token:
        raise FlutterwaveError(data.get('error_description') or data.get('message') or 'Unable to authenticate with Flutterwave.')
    return token


def _payment_amount_matches(received_amount, expected_amount):
    try:
        return Decimal(str(received_amount)).quantize(Decimal('0.01')) == expected_amount.quantize(Decimal('0.01'))
    except Exception:
        return False


def _mark_payment_from_charge(payment, charge):
    payment.gateway_response = json.dumps(charge)
    payment.gateway_transaction_id = charge.get('id') or payment.gateway_transaction_id
    
    if (
        charge.get('reference') == payment.reference
        and charge.get('status') == 'succeeded'
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
    token = _get_flutterwave_token()
    call


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
import json
import uuid
from decimal import Decimal

import requests
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from orders.models import Order
from .models import Payment


MOBILE_MONEY_NETWORKS = [
    ('MTN', 'MTN Mobile Money'),
    ('VODAFONE', 'Telecel Cash'),
    ('AIRTELTIGO', 'AirtelTigo Money'),
]


class FlutterwaveError(Exception):
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
    data = response.json()
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
    callback_url = request.build_absolute_uri(reverse('payments:verify', args=[payment.reference]))
    payload = {
        'amount': str(order.total),
        'currency': settings.FLUTTERWAVE_CURRENCY,
        'reference': payment.reference,
        'redirect_url': callback_url,
        'customer': {
            'address': {
                'country': 'GH',
                'city': order.city,
                'state': order.region,
                'line1': order.address,
            },
            'email': order.email,
            'name': {
                'first': order.first_name,
                'last': order.last_name,
            },
            'phone': {
                'country_code': '233',
                'number': order.phone.lstrip('+').removeprefix('233'),
            },
        },
        'payment_method': {
            'type': 'mobile_money',
            'mobile_money': {
                'country_code': '233',
                'network': network,
                'phone_number': phone_number.lstrip('+').removeprefix('233'),
            },
        },
        'meta': {
            'order_number': order.order_number,
        },
    }
    response = requests.post(
        f'{settings.FLUTTERWAVE_BASE_URL.rstrip("/")}/orchestration/direct-charges',
        json=payload,
        headers=_flutterwave_headers(token, idempotency_key=f'charge-{payment.reference}'),
        timeout=20,
    )
    data = response.json()
    if response.status_code >= 400 or data.get('status') != 'success':
        raise FlutterwaveError(data.get('message') or 'Flutterwave could not start this payment.')

    charge = data.get('data') or {}
    payment.gateway_transaction_id = charge.get('id', '')
    payment.gateway_response = json.dumps(charge)
    payment.status = 'pending'
    payment.save()
    return charge


@require_http_methods(['GET', 'POST'])
def initiate_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    reference = f"GS-{order.order_number}-{uuid.uuid4().hex[:6].upper()}"
    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            'reference': reference,
            'amount': order.total,
        },
    )
    if not created and payment.status != 'success':
        payment.amount = order.total
        payment.save(update_fields=['amount'])

    context = {
        'order': order,
        'payment': payment,
        'networks': MOBILE_MONEY_NETWORKS,
        'currency': settings.FLUTTERWAVE_CURRENCY,
    }

    if request.method == 'POST':
        network = request.POST.get('network', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        if network not in dict(MOBILE_MONEY_NETWORKS) or not phone_number:
            messages.error(request, 'Choose a mobile money network and enter the payment phone number.')
            return render(request, 'payments/initiate.html', context)

        try:
            charge = _create_mobile_money_charge(request, order, payment, network, phone_number)
            next_action = charge.get('next_action') or {}
            if next_action.get('type') == 'redirect_url':
                redirect_url = (next_action.get('redirect_url') or {}).get('url')
                if redirect_url:
                    return redirect(redirect_url)

            instruction = (next_action.get('payment_instruction') or {}).get('note')
            if instruction:
                context['payment_instruction'] = instruction
            else:
                messages.info(request, 'Payment started. Approve the prompt on your phone, then verify the payment.')
            return render(request, 'payments/initiate.html', context)
        except Exception as exc:
            messages.error(request, str(exc))

    return render(request, 'payments/initiate.html', context)


def verify_payment(request, reference):
    payment = get_object_or_404(Payment, reference=reference)
    if not payment.gateway_transaction_id:
        messages.error(request, 'No Flutterwave charge ID is available for this payment yet.')
        return render(request, 'payments/failed.html', {'order': payment.order})

    try:
        token = _get_flutterwave_token()
        response = requests.get(
            f'{settings.FLUTTERWAVE_BASE_URL.rstrip("/")}/charges/{payment.gateway_transaction_id}',
            headers=_flutterwave_headers(token),
            timeout=15,
        )
        data = response.json()
        charge = data.get('data') or {}

        if response.status_code < 400 and data.get('status') == 'success' and _mark_payment_from_charge(payment, charge):
            return redirect('orders:confirmation', order_number=payment.order.order_number)

        messages.error(request, 'Flutterwave has not confirmed this payment yet. Please try again after approving it.')
        return render(request, 'payments/failed.html', {'order': payment.order})
    except Exception as exc:
        return render(request, 'payments/failed.html', {'order': payment.order, 'error': str(exc)})


@csrf_exempt
def flutterwave_webhook(request):
    """Handle Flutterwave charge webhook events."""
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        if payload.get('type') == 'charge.completed':
            charge = payload.get('data') or {}
            reference = charge.get('reference')
            try:
                payment = Payment.objects.get(reference=reference)
                _mark_payment_from_charge(payment, charge)
            except Payment.DoesNotExist:
                pass

    return HttpResponse(status=200)

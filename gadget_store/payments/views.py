import uuid
import requests
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone
from orders.models import Order
from .models import Payment


def initiate_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Create payment reference
    reference = f"GS-{order.order_number}-{uuid.uuid4().hex[:6].upper()}"
    
    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            'reference': reference,
            'amount': order.total,
        }
    )
    
    context = {
        'order': order,
        'payment': payment,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        'amount_kobo': int(order.total * 100),  # Paystack uses pesewas/kobo
    }
    return render(request, 'payments/initiate.html', context)


@csrf_exempt
def verify_payment(request, reference):
    payment = get_object_or_404(Payment, reference=reference)
    
    # Verify with Paystack API
    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    url = f'https://api.paystack.co/transaction/verify/{reference}'
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('status') and data['data']['status'] == 'success':
            payment.status = 'success'
            payment.paid_at = timezone.now()
            payment.gateway_response = json.dumps(data['data'])
            payment.save()
            
            order = payment.order
            order.status = 'paid'
            order.save()
            
            return redirect('orders:confirmation', order_number=order.order_number)
        else:
            payment.status = 'failed'
            payment.gateway_response = json.dumps(data)
            payment.save()
            return render(request, 'payments/failed.html', {'order': payment.order})
    except Exception as e:
        return render(request, 'payments/failed.html', {'order': payment.order, 'error': str(e)})


@csrf_exempt
def paystack_webhook(request):
    """Handle Paystack webhook events"""
    if request.method == 'POST':
        payload = json.loads(request.body)
        event = payload.get('event')
        
        if event == 'charge.success':
            reference = payload['data']['reference']
            try:
                payment = Payment.objects.get(reference=reference)
                payment.status = 'success'
                payment.paid_at = timezone.now()
                payment.save()
                payment.order.status = 'paid'
                payment.order.save()
            except Payment.DoesNotExist:
                pass
    
    return HttpResponse(status=200)

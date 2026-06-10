from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal
from .models import Order, OrderItem
from .forms import CheckoutForm
from store.models import Product, Profile


def checkout(request):
    if not request.user.is_authenticated:
        messages.info(request, 'Please log in to proceed with checkout.')
        return redirect(f"{settings.LOGIN_URL}?next={request.path}")
    
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, 'Your cart is empty.')
        return redirect('store:cart')

    cart_items = []
    subtotal = 0
    product_ids = [int(pid) for pid in cart.keys()]
    products_map = Product.objects.in_bulk(product_ids)
    
    for pid_str, item in cart.items():
        product = products_map.get(int(pid_str))
        if product:
            item_total = product.effective_price * item.get('quantity', 1)
            subtotal += item_total
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'item_total': item_total,
            })

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            region = form.cleaned_data['region']
            delivery_fee = Decimal(settings.DELIVERY_REGIONS.get(region, 50.00))
            total = subtotal + delivery_fee
            
            order = form.save(commit=False)
            order.subtotal = subtotal
            order.delivery_fee = delivery_fee
            order.total = total
            if request.user.is_authenticated:
                order.user = request.user
            order.save()
            
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    product_name=item['product'].name,
                    price=item['product'].effective_price,
                    quantity=item['quantity'],
                )
            
            # Clear cart
            request.session['cart'] = {}
            request.session.modified = True
            
            # Store order id in session for payment
            request.session['pending_order_id'] = order.id
            return redirect('payments:initiate', order_id=order.id)
    else:
        initial = {}
        if request.user.is_authenticated:
            profile = Profile.objects.filter(user=request.user).first()
            initial = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
            if profile:
                initial.update({
                    'phone': profile.phone,
                    'address': profile.address,
                    'city': profile.city,
                    'region': profile.region,
                })
        form = CheckoutForm(initial=initial)

    context = {
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_regions': settings.DELIVERY_REGIONS,
    }
    return render(request, 'orders/checkout.html', context)


def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'orders/order_detail.html', {'order': order})


def order_confirmation(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'orders/confirmation.html', {'order': order})


def my_orders(request):
    if not request.user.is_authenticated:
        return redirect('login')
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})


@require_POST
def cancel_order(request, order_id):
    """Cancel a pending order (AJAX endpoint)."""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    
    # Check permission: user must be owner or staff
    if order.user != request.user and not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Only allow cancelling pending orders
    if order.status != 'pending':
        return JsonResponse({'error': f'Cannot cancel {order.status} orders'}, status=400)
    
    order.status = 'cancelled'
    order.notes = (order.notes or '') + f"\nCancelled by user on {order.updated_at.strftime('%Y-%m-%d %H:%M')}"
    order.save(update_fields=['status', 'notes', 'updated_at'])
    
    return JsonResponse({'ok': True, 'message': 'Order cancelled successfully', 'status': order.status})


@require_POST
def delete_order(request, order_id):
    """Delete an order (AJAX endpoint, staff only)."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    
    order_number = order.order_number
    order.delete()
    
    return JsonResponse({'ok': True, 'message': f'Order {order_number} deleted', 'order_id': order_id})

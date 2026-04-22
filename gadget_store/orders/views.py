from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from .models import Order, OrderItem
from .forms import CheckoutForm
from store.models import Product


def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, 'Your cart is empty.')
        return redirect('store:cart')

    cart_items = []
    subtotal = 0
    for product_id, item in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            item_total = product.effective_price * item['quantity']
            subtotal += item_total
            cart_items.append({'product': product, 'quantity': item['quantity'], 'item_total': item_total})
        except Product.DoesNotExist:
            pass

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            region = form.cleaned_data['region']
            delivery_fee = settings.DELIVERY_REGIONS.get(region, 50.00)
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
                # Reduce stock
                p = item['product']
                p.stock = max(0, p.stock - item['quantity'])
                p.save()
            
            # Clear cart
            request.session['cart'] = {}
            request.session.modified = True
            
            # Store order id in session for payment
            request.session['pending_order_id'] = order.id
            return redirect('payments:initiate', order_id=order.id)
    else:
        initial = {}
        if request.user.is_authenticated:
            initial = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
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

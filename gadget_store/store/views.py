from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Product, Category
import json


def home(request):
    featured_products = Product.objects.filter(is_featured=True, is_active=True)[:8]
    categories = Category.objects.all()
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'new_arrivals': new_arrivals,
    }
    return render(request, 'store/home.html', context)


def product_list(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()
    
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q')
    sort_by = request.GET.get('sort', 'newest')
    
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)
    
    if search_query:
        products = products.filter(name__icontains=search_query) | products.filter(description__icontains=search_query)
    
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    else:
        products = products.order_by('-created_at')
    
    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'store/product_list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product.id)[:4]
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'store/product_detail.html', context)


def cart(request):
    cart_data = request.session.get('cart', {})
    cart_items = []
    subtotal = 0
    
    for product_id, item in cart_data.items():
        try:
            product = Product.objects.get(id=product_id)
            item_total = product.effective_price * item['quantity']
            subtotal += item_total
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'item_total': item_total,
            })
        except Product.DoesNotExist:
            pass
    
    context = {'cart_items': cart_items, 'subtotal': subtotal}
    return render(request, 'store/cart.html', context)


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    cart = request.session.get('cart', {})
    pid = str(product_id)
    
    if pid in cart:
        cart[pid]['quantity'] += quantity
    else:
        cart[pid] = {'quantity': quantity}
    
    request.session['cart'] = cart
    request.session.modified = True
    
    total_items = sum(v['quantity'] for v in cart.values())
    messages.success(request, f'"{product.name}" added to cart!')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'cart_count': total_items})
    
    return cart_view(request)


@require_POST
def update_cart(request, product_id):
    quantity = int(request.POST.get('quantity', 1))
    cart = request.session.get('cart', {})
    pid = str(product_id)
    
    if quantity <= 0:
        cart.pop(pid, None)
    else:
        cart[pid] = {'quantity': quantity}
    
    request.session['cart'] = cart
    request.session.modified = True
    return JsonResponse({'success': True})


@require_POST
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    cart.pop(str(product_id), None)
    request.session['cart'] = cart
    request.session.modified = True
    messages.info(request, 'Item removed from cart.')
    return JsonResponse({'success': True})


def cart_view(request):
    from django.shortcuts import redirect
    return redirect('store:cart')

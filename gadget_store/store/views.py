from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.db.models import Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth import login, update_session_auth_hash
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .forms import SignupForm, ProfileForm
from django.conf import settings
from .models import Product, Category, Profile, Review
import json


def home(request):
    featured_products = Product.objects.filter(is_featured=True, is_active=True).annotate(avg_rating=Avg('reviews__rating'))[:8]
    categories = Category.objects.all()
    new_arrivals = Product.objects.filter(is_active=True).annotate(avg_rating=Avg('reviews__rating')).order_by('-created_at')[:8]
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'new_arrivals': new_arrivals,
    }
    return render(request, 'store/home.html', context)


def product_list(request):
    products = Product.objects.filter(is_active=True).annotate(avg_rating=Avg('reviews__rating'))
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
    
    if request.method == 'POST' and request.user.is_authenticated:
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        if rating and comment:
            Review.objects.create(
                product=product,
                user=request.user,
                rating=rating,
                comment=comment
            )
            messages.success(request, 'Thank you for your review!')
            return redirect('store:product_detail', slug=slug)

    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).annotate(avg_rating=Avg('reviews__rating')).exclude(id=product.id)[:4]
    
    reviews = product.reviews.all()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    
    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'avg_rating': avg_rating,
    }
    return render(request, 'store/product_detail.html', context)


def cart(request):
    cart_data = request.session.get('cart', {})
    # Optimization: Fetch all products in one query to avoid N+1 hits
    product_ids = [int(pid) for pid in cart_data.keys()]
    products_map = Product.objects.in_bulk(product_ids)
    
    cart_items = []
    subtotal = 0
    
    for pid_str, item in cart_data.items():
        product = products_map.get(int(pid_str))
        if product:
            item_total = product.effective_price * item.get('quantity', 1)
            subtotal += item_total
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'item_total': item_total,
            })
    
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
    
    return redirect('store:cart')


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
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect('store:cart')


def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.save()
            Profile.objects.create(user=user, phone=form.cleaned_data['phone'])
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('store:home')
    else:
        form = SignupForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def account_settings(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        password_form = PasswordChangeForm(request.user, request.POST)

        if 'update_profile' in request.POST:
            if profile_form.is_valid():
                # Update core User fields manually
                request.user.first_name = request.POST.get('first_name', '')
                request.user.last_name = request.POST.get('last_name', '')
                email = request.POST.get('email', '')
                if email != request.user.email:
                    if User.objects.filter(email=email).exclude(id=request.user.id).exists():
                        messages.error(request, 'Email already in use.')
                        return redirect('store:account_settings')
                    request.user.email = email
                request.user.save()
                
                profile_form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('store:account_settings')
            else:
                messages.error(request, 'Please correct the errors below.')
            
        elif 'change_password' in request.POST:
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password was successfully updated!')
                return redirect('store:account_settings')
            else:
                messages.error(request, 'Please correct the error below.')
    else:
        password_form = PasswordChangeForm(request.user)
        profile_form = ProfileForm(instance=profile)

    context = {
        'profile': profile,
        'profile_form': profile_form,
        'password_form': password_form,
        'delivery_regions': settings.DELIVERY_REGIONS,  # Assuming settings is imported
    }
    return render(request, 'store/account_settings.html', context)


def category(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, is_active=True).annotate(avg_rating=Avg('reviews__rating'))
    categories = Category.objects.all()

    context = {
        'category': category,
        'products': products,
        'categories': categories,
        'selected_category': category,
    }
    return render(request, 'store/product_list.html', context)


def help_support(request):
    return render(request, 'store/help_support.html')

def search_suggestions(request):
    """AJAX endpoint for product search suggestions."""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    products = Product.objects.filter(
        is_active=True, 
        name__icontains=query
    )[:5]
    
    results = [{
        'name': p.name,
        'price': float(p.effective_price),
        'url': p.get_absolute_url(),
        'image': p.get_mobile_thumbnail_url() if p.image else None,
        'category': p.category.name if p.category else ""
    } for p in products]
    
    return JsonResponse({'results': results})

def track_order(request):
    """View to handle live order tracking status."""
    order_number = request.GET.get('order_number', '').strip()
    order = None
    if order_number:
        from orders.models import Order
        order = Order.objects.filter(order_number=order_number).first()
        
    return render(request, 'store/tracker.html', {'order': order, 'order_number': order_number})

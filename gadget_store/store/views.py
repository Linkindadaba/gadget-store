from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django import forms
from django.contrib.auth.models import User


class SignupForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    phone = forms.CharField(max_length=20, label='Phone Number')
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already in use.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data
from django.conf import settings
from .models import Product, Category, Profile
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
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect('store:cart')


def cart_view(request):
    from django.shortcuts import redirect
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


def account_settings(request):
    if not request.user.is_authenticated:
        return redirect('login')
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':        # Update user
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        if email != request.user.email:
            if User.objects.filter(email=email).exclude(id=request.user.id).exists():
                messages.error(request, 'Email already in use.')
                return redirect('store:account_settings')
            request.user.email = email
        request.user.save()
        
        # Update profile        profile.phone = request.POST.get('phone', '')
        profile.address = request.POST.get('address', '')
        profile.city = request.POST.get('city', '')
        profile.region = request.POST.get('region', '')
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('store:account_settings')
    context = {
        'profile': profile,
        'delivery_regions': settings.DELIVERY_REGIONS,  # Assuming settings is imported
    }
    return render(request, 'store/account_settings.html', context)

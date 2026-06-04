from django.conf import settings
from .models import Category
from django.core.cache import cache

def cart_count(request):
    cart = request.session.get('cart', {})
    count = sum(v['quantity'] for v in cart.values())
    return {'cart_count': count}

def social_media_links(request):
    return {'SOCIAL_MEDIA': settings.SOCIAL_MEDIA}

def categories(request):
    nav_categories = cache.get('nav_categories')
    if nav_categories is None:
        nav_categories = Category.objects.all()
        cache.set('nav_categories', nav_categories, 3600)  # Cache for 1 hour
    return {'nav_categories': nav_categories}


def support_contacts(request):
    return {'SUPPORT_CONTACTS': settings.SUPPORT_CONTACTS}

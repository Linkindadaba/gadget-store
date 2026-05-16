from django.conf import settings

def cart_count(request):
    cart = request.session.get('cart', {})
    count = sum(v['quantity'] for v in cart.values())
    return {'cart_count': count}

def social_media_links(request):
    return {'SOCIAL_MEDIA': settings.SOCIAL_MEDIA}

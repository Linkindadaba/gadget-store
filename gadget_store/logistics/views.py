from django.http import JsonResponse
from .models import DeliveryZone
from django.conf import settings


def get_delivery_fee(request):
    region = request.GET.get('region', '')
    try:
        zone = DeliveryZone.objects.get(region=region, is_active=True)
        return JsonResponse({'fee': float(zone.fee), 'estimated_days': zone.estimated_days})
    except DeliveryZone.DoesNotExist:
        fee = settings.DELIVERY_REGIONS.get(region, 50.00)
        return JsonResponse({'fee': fee, 'estimated_days': '3-7 business days'})


def delivery_zones(request):
    zones = DeliveryZone.objects.filter(is_active=True).values('region', 'fee', 'estimated_days')
    return JsonResponse({'zones': list(zones)})

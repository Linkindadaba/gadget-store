from decimal import Decimal

from django.test import TestCase

from .models import DeliveryZone


class DeliveryZoneModelTests(TestCase):
    def test_str_returns_region_and_fee(self):
        zone = DeliveryZone.objects.create(region='Greater Accra', fee=Decimal('12.50'))
        self.assertEqual(str(zone), 'Greater Accra - GHS 12.50')

    def test_ordering_by_region(self):
        DeliveryZone.objects.create(region='Ashanti', fee=Decimal('8.00'))
        DeliveryZone.objects.create(region='Greater Accra', fee=Decimal('12.50'))
        zones = list(DeliveryZone.objects.all())
        self.assertEqual(zones[0].region, 'Ashanti')
        self.assertEqual(zones[1].region, 'Greater Accra')

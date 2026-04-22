from django.core.management.base import BaseCommand
from store.models import Category, Product
from logistics.models import DeliveryZone
from django.conf import settings


class Command(BaseCommand):
    help = 'Seed database with demo data'

    def handle(self, *args, **kwargs):
        # Seed delivery zones
        for region, fee in settings.DELIVERY_REGIONS.items():
            DeliveryZone.objects.get_or_create(region=region, defaults={'fee': fee})
        self.stdout.write('✅ Delivery zones seeded')

        # Categories
        cats = [
            ('Smartphones', 'bi-phone', 'Latest smartphones and mobile phones'),
            ('Earbuds & Headphones', 'bi-headphones', 'Wireless and wired audio'),
            ('Smartwatches', 'bi-smartwatch', 'Smart wearables'),
            ('Laptop Accessories', 'bi-laptop', 'Bags, stands, keyboards and more'),
            ('Chargers & Cables', 'bi-plug', 'Fast chargers and cables'),
            ('Phone Cases', 'bi-phone-flip', 'Protective cases and covers'),
        ]
        cat_objs = {}
        for name, icon, desc in cats:
            cat, _ = Category.objects.get_or_create(name=name, defaults={'icon': icon, 'description': desc})
            cat_objs[name] = cat
        self.stdout.write('✅ Categories seeded')

        # Products
        products = [
            ('iPhone 15 Pro Max 256GB', 'Smartphones', 8999, None, 5, True, 'Latest Apple flagship with titanium design, A17 Pro chip, and 48MP camera system.'),
            ('Samsung Galaxy S24 Ultra', 'Smartphones', 7500, 6999, 8, True, 'Samsung\'s most powerful phone with built-in S Pen, 200MP camera and Galaxy AI.'),
            ('Tecno Phantom X2 Pro', 'Smartphones', 3200, 2800, 12, False, 'Premium Tecno flagship with retractable portrait lens and Dimensity 9000 chip.'),
            ('AirPods Pro 2nd Gen', 'Earbuds & Headphones', 1800, 1500, 15, True, 'Active noise cancellation, Adaptive Audio, and up to 30hrs battery life.'),
            ('Samsung Galaxy Buds2 Pro', 'Earbuds & Headphones', 1200, None, 20, False, 'Hi-Fi 24-bit audio, intelligent ANC, and IPX7 water resistance.'),
            ('Apple Watch Series 9', 'Smartwatches', 3500, 3200, 7, True, 'The most advanced Apple Watch with Double Tap gesture and brighter display.'),
            ('Samsung Galaxy Watch 6', 'Smartwatches', 2200, 1900, 10, False, 'Advanced health tracking, sleep coaching, and 3-day battery life.'),
            ('Anker 65W GaN Charger', 'Chargers & Cables', 250, None, 50, False, 'Ultra-compact 65W GaN charger with 2 USB-C and 1 USB-A ports.'),
            ('Baseus 100W USB-C Cable 2m', 'Chargers & Cables', 80, None, 100, False, 'Braided nylon 100W fast charge cable, supports up to 100W power delivery.'),
            ('iPhone 15 Pro Silicone Case', 'Phone Cases', 120, 99, 30, False, 'Premium silicone case with MagSafe compatibility and microfibre lining.'),
            ('Laptop Stand Adjustable', 'Laptop Accessories', 180, None, 25, False, 'Ergonomic aluminium laptop stand, adjustable height, supports up to 17 inches.'),
            ('Logitech MX Keys Mini', 'Laptop Accessories', 750, 680, 8, True, 'Compact wireless keyboard with smart illumination and multi-device connectivity.'),
        ]

        for name, cat_name, price, disc, stock, featured, desc in products:
            cat = cat_objs.get(cat_name)
            Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': cat,
                    'price': price,
                    'discount_price': disc,
                    'stock': stock,
                    'is_featured': featured,
                    'description': desc,
                    'is_active': True,
                }
            )
        self.stdout.write('✅ Products seeded')
        self.stdout.write(self.style.SUCCESS('\n🎉 Demo data ready! Run: python manage.py runserver'))

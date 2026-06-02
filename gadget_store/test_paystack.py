import os
import sys
from decimal import Decimal
import uuid

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gadget_store.settings')

import django
from django.test import Client

django.setup()

from store.models import Category, Product
from orders.models import Order, OrderItem

cat, _ = Category.objects.get_or_create(name='Test', slug='test')
prod, _ = Product.objects.get_or_create(
    name='Test Product',
    defaults={
        'slug': 'test-product',
        'description': 'Test product for payment flow',
        'price': Decimal('10.00'),
        'stock': 10,
        'is_active': True,
        'category': cat,
    }
)

order = Order.objects.create(
    order_number=str(uuid.uuid4()).upper()[:12],
    first_name='Test',
    last_name='Buyer',
    email='test@example.com',
    phone='0241234567',
    address='123 Street',
    city='Accra',
    region='Greater Accra',
    subtotal=Decimal('10.00'),
    delivery_fee=Decimal('15.00'),
    total=Decimal('25.00'),
    status='pending',
)
OrderItem.objects.create(
    order=order,
    product=prod,
    product_name=prod.name,
    price=Decimal('10.00'),
    quantity=1,
)

client = Client()
response = client.post(f'/payments/initiate/{order.id}/', {'gateway': 'paystack'})
print('status_code:', response.status_code)
print('redirect:', response.url if getattr(response, 'url', None) else 'none')
print('content:', response.content[:1000])

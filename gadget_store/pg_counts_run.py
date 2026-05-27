import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gadget_store.settings')
if 'DATABASE_URL' not in os.environ:
    raise SystemExit('Set DATABASE_URL before running')

django.setup()
from store.models import Product
from orders.models import Order
from payments.models import Payment
from django.contrib.auth import get_user_model

print('Products:', Product.objects.count())
print('Orders:', Order.objects.count())
print('Payments:', Payment.objects.count())
User = get_user_model()
print('Users:', User.objects.count())

from decimal import Decimal

from django.test import TestCase

from .models import Order, OrderItem
from store.models import Category, Product


class OrderModelTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            first_name='Jane',
            last_name='Doe',
            email='jane@example.com',
            phone='0244000000',
            address='123 Main Road',
            city='Accra',
            region='Greater Accra',
            subtotal=Decimal('95.00'),
            delivery_fee=Decimal('5.00'),
            total=Decimal('100.00'),
        )

    def test_order_number_is_generated_if_blank(self):
        self.assertTrue(self.order.order_number)
        self.assertEqual(len(self.order.order_number), 12)

    def test_full_name_property(self):
        self.assertEqual(self.order.full_name, 'Jane Doe')

    def test_get_total_amount_returns_total(self):
        self.assertEqual(self.order.get_total_amount(), Decimal('100.00'))

    def test_str_returns_order_number(self):
        self.assertEqual(str(self.order), f'Order #{self.order.order_number}')


class OrderItemModelTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Electronics')
        product = Product.objects.create(
            category=category,
            name='Smart Lamp',
            description='Wi-Fi enabled lamp',
            price=Decimal('45.00'),
            stock=20,
        )
        self.order = Order.objects.create(
            first_name='Liam',
            last_name='Smith',
            email='liam@example.com',
            phone='0244000001',
            address='456 Tech Lane',
            city='Kumasi',
            region='Ashanti',
            subtotal=Decimal('45.00'),
            delivery_fee=Decimal('5.00'),
            total=Decimal('50.00'),
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=product,
            product_name=product.name,
            price=product.price,
            quantity=2,
        )

    def test_item_total_calculation(self):
        self.assertEqual(self.order_item.item_total, Decimal('90.00'))

    def test_order_item_str(self):
        self.assertEqual(str(self.order_item), '2x Smart Lamp')

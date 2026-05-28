from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category, Product, Profile, Review


class CategoryModelTests(TestCase):
    def test_slug_is_generated_on_save(self):
        category = Category.objects.create(name='Mobile Accessories')
        self.assertEqual(category.slug, 'mobile-accessories')

    def test_str_returns_name(self):
        category = Category.objects.create(name='Audio Gear')
        self.assertEqual(str(category), 'Audio Gear')


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Audio Gear')

    def test_slug_is_generated_on_save(self):
        product = Product.objects.create(
            category=self.category,
            name='Wireless Headphones',
            description='Comfortable over-ear headphones',
            price=Decimal('120.00'),
            stock=10,
        )
        self.assertEqual(product.slug, 'wireless-headphones')

    def test_effective_price_uses_discount_price_when_present(self):
        product = Product.objects.create(
            category=self.category,
            name='Smart Speaker',
            description='Voice activated speaker',
            price=Decimal('150.00'),
            discount_price=Decimal('120.00'),
            stock=5,
        )
        self.assertEqual(product.effective_price, Decimal('120.00'))

    def test_discount_percent_computes_correctly(self):
        product = Product.objects.create(
            category=self.category,
            name='Smart Watch',
            description='Fitness tracking watch',
            price=Decimal('200.00'),
            discount_price=Decimal('150.00'),
            stock=8,
        )
        self.assertEqual(product.discount_percent, 25)

    def test_in_stock_property(self):
        available = Product.objects.create(
            category=self.category,
            name='Portable Charger',
            description='10000mAh power bank',
            price=Decimal('40.00'),
            stock=3,
        )
        out_of_stock = Product.objects.create(
            category=self.category,
            name='USB Cable',
            description='Durable charging cable',
            price=Decimal('10.00'),
            stock=0,
        )
        self.assertTrue(available.in_stock)
        self.assertFalse(out_of_stock.in_stock)

    def test_get_absolute_url_returns_product_detail_path(self):
        product = Product.objects.create(
            category=self.category,
            name='Bluetooth Earbuds',
            description='Noise cancelling earbuds',
            price=Decimal('80.00'),
            stock=12,
        )
        expected_url = reverse('store:product_detail', kwargs={'slug': product.slug})
        self.assertEqual(product.get_absolute_url(), expected_url)

    def test_average_rating_returns_zero_when_no_reviews(self):
        product = Product.objects.create(
            category=self.category,
            name='Gaming Mouse',
            description='Precision wireless mouse',
            price=Decimal('90.00'),
            stock=6,
        )
        self.assertEqual(product.average_rating, 0)

    def test_average_rating_computes_average_rating(self):
        user = User.objects.create_user(username='customer', password='pass')
        product = Product.objects.create(
            category=self.category,
            name='Mechanical Keyboard',
            description='RGB mechanical keyboard',
            price=Decimal('110.00'),
            stock=4,
        )
        Review.objects.create(product=product, user=user, rating=4, comment='Great feel')
        Review.objects.create(product=product, user=user, rating=2, comment='Too loud')
        self.assertEqual(product.average_rating, 3)


class ProfileModelTests(TestCase):
    def test_profile_str_includes_username(self):
        user = User.objects.create_user(username='janedoe', email='jane@example.com', password='testpass')
        profile = Profile.objects.create(user=user, phone='0244000000', city='Accra', region='Greater Accra')
        self.assertEqual(str(profile), 'Profile for janedoe')


class ReviewModelTests(TestCase):
    def test_review_str_format(self):
        user = User.objects.create_user(username='alex', password='testpass')
        category = Category.objects.create(name='Wearables')
        product = Product.objects.create(
            category=category,
            name='Fitness Band',
            description='Tracks your activity',
            price=Decimal('70.00'),
            stock=7,
        )
        review = Review.objects.create(product=product, user=user, rating=5, comment='Excellent')
        self.assertEqual(str(review), 'alex - Fitness Band (5)')

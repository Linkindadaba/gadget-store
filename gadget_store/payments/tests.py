import json
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from orders.models import Order
from .models import Payment

class PaymentModelTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone="0244000000",
            address="456 Gadget Lane",
            city="Kumasi",
            region="Ashanti",
            subtotal=Decimal("45.00"),
            delivery_fee=Decimal("5.00"),
            total=Decimal("50.00"),
            order_number="ORD-999"
        )

    def test_payment_creation_and_defaults(self):
        """Test that a payment is created with the correct defaults."""
        payment = Payment.objects.create(
            order=self.order,
            reference="TEST-REF",
            amount=Decimal("50.00")
        )
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.gateway, 'flutterwave')
        self.assertEqual(
            str(payment), 
            f"Payment for {self.order.order_number} [flutterwave] - pending"
        )

    def test_payment_one_to_one_relationship(self):
        """Ensure the OneToOne relationship with Order works as expected."""
        payment = Payment.objects.create(
            order=self.order,
            reference="TEST-REF-2",
            amount=Decimal("50.00")
        )
        self.assertEqual(self.order.payment, payment)

class PaymentUtilityTests(TestCase):
    def test_payment_amount_matches(self):
        """Verify amount matching with decimal quantization."""
        from .views import _payment_amount_matches
        self.assertTrue(_payment_amount_matches(100.0, Decimal("100.00")))
        self.assertTrue(_payment_amount_matches("100.001", Decimal("100.00")))
        self.assertFalse(_payment_amount_matches(100.05, Decimal("100.00")))

    def test_get_payment_gateway_logic(self):
        """Test utility that determines gateway from payment object or reference."""
        from .views import _get_payment_gateway
        order = Order.objects.create(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            phone="0244000000",
            address="1 Test Road",
            city="Accra",
            region="Greater Accra",
            subtotal=Decimal("0.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("0.00"),
            order_number="TEST-1"
        )
        
        p1 = Payment(order=order, gateway='paystack')
        self.assertEqual(_get_payment_gateway(p1), 'paystack')
        
        p2 = Payment(order=order, gateway='', reference='PAY-ORDER-1')
        self.assertEqual(_get_payment_gateway(p2), 'paystack')
        
        p3 = Payment(order=order, gateway='', reference='FLW-ORDER-1')
        self.assertEqual(_get_payment_gateway(p3), 'flutterwave')

class PaymentWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.order = Order.objects.create(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="0244000000",
            address="123 Tech Street",
            city="Accra",
            region="Greater Accra",
            subtotal=Decimal("90.00"),
            delivery_fee=Decimal("10.00"),
            total=Decimal("100.00"),
            status='pending',
            order_number="ORD-123"
        )
        self.payment = Payment.objects.create(
            order=self.order,
            reference="PAY-REF-123",
            amount=Decimal("100.00"),
            gateway='paystack',
            status='pending'
        )

    @patch('payments.views.requests.post')
    def test_initiate_paystack_payment(self, mock_post):
        """Verify Paystack link generation logic."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "status": True,
            "data": {"authorization_url": "https://checkout.paystack.com/test"}
        }
        
        response = self.client.post(reverse('payments:initiate', args=[self.order.id]), {
            'gateway': 'paystack'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertIn("checkout.paystack.com", response.url)

    @patch('payments.views.hmac.compare_digest')
    def test_paystack_webhook_success(self, mock_compare):
        """Verify Paystack webhook marks order as paid."""
        mock_compare.return_value = True
        payload = {
            "event": "charge.success",
            "data": {
                "reference": self.payment.reference,
                "status": "success",
                "amount": 10000, # Paystack sends in kobo
                "currency": "GHS",
                "id": "GT-ID-999"
            }
        }
        
        headers = {'HTTP_X_PAYSTACK_SIGNATURE': 'fake_sig'}
        response = self.client.post(
            reverse('payments:webhook'),
            data=json.dumps(payload),
            content_type='application/json',
            **headers
        )
        
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, 'success')
        self.assertEqual(self.order.status, 'paid')

    @patch('payments.views.hmac.compare_digest')
    def test_flutterwave_webhook_success(self, mock_compare):
        """Verify Flutterwave webhook logic."""
        self.payment.gateway = 'flutterwave'
        self.payment.reference = 'FLW-REF-123'
        self.payment.save()
        
        mock_compare.return_value = True
        payload = {
            "event": "charge.completed",
            "data": {
                "tx_ref": self.payment.reference,
                "status": "successful",
                "amount": 100.00,
                "currency": "GHS",
                "id": 123456
            }
        }
        
        headers = {'HTTP_VERIF_HASH': settings.FLUTTERWAVE_WEBHOOK_SECRET}
        response = self.client.post(
            reverse('payments:webhook'),
            data=json.dumps(payload),
            content_type='application/json',
            **headers
        )
        
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'success')

    def test_invalid_webhook_signature(self):
        """Webhooks with bad signatures should be rejected."""
        response = self.client.post(
            reverse('payments:webhook'),
            data=json.dumps({"event": "test"}),
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE='wrong_sig'
        )
        self.assertEqual(response.status_code, 400)

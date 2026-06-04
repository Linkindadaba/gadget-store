from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging
from .models import Order

logger = logging.getLogger(__name__)

@shared_task
def send_order_confirmation_email(order_id):
    """
    Sends a confirmation email to the customer after successful payment.
    """
    try:
        order = Order.objects.get(id=order_id)
        subject = f"Order Confirmation - {order.order_number}"
        
        # Assumes you have an email template at templates/emails/order_confirmation.html
        html_message = render_to_string('emails/order_confirmation.html', {'order': order})
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject, plain_message, settings.DEFAULT_FROM_EMAIL, 
            [order.email], html_message=html_message
        )
        logger.info(f"Sent confirmation email for order {order.order_number}")
    except Order.DoesNotExist:
        logger.error(f"Task failed: Order {order_id} not found.")
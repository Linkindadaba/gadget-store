from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('initiate/<int:order_id>/', views.initiate_payment, name='initiate'),
    path('webhook/', views.flutterwave_webhook, name='webhook'),
    path('callback/', views.payment_callback, name='payment_callback'),
]

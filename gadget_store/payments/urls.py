from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('initiate/<int:order_id>/', views.initiate_payment, name='initiate'),
    path('verify/<str:reference>/', views.verify_payment, name='verify'),
    path('webhook/', views.paystack_webhook, name='webhook'),
]

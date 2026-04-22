from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('<str:order_number>/', views.order_detail, name='order_detail'),
    path('<str:order_number>/confirmation/', views.order_confirmation, name='confirmation'),
    path('my-orders/', views.my_orders, name='my_orders'),
]

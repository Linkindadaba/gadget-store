from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('<int:order_id>/delete/', views.delete_order, name='delete_order'),
    path('<str:order_number>/confirmation/', views.order_confirmation, name='confirmation'),
    path('<str:order_number>/', views.order_detail, name='order_detail'),
]

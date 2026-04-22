from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    path('fee/', views.get_delivery_fee, name='get_fee'),
    path('zones/', views.delivery_zones, name='zones'),
]

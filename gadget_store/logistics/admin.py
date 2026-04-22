from django.contrib import admin
from .models import DeliveryZone

@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ['region', 'fee', 'estimated_days', 'is_active']
    list_editable = ['fee', 'is_active']

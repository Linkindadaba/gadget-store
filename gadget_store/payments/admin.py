from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'gateway', 'order', 'amount', 'status', 'paid_at', 'created_at']
    list_filter = ['status', 'gateway']
    readonly_fields = ['reference', 'order', 'amount', 'gateway', 'gateway_response', 'paid_at', 'created_at']

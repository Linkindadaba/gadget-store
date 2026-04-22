from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ['product_name', 'price', 'quantity', 'item_total']
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'full_name', 'email', 'region', 'total', 'status', 'created_at']
    list_filter = ['status', 'region', 'created_at']
    list_editable = ['status']
    search_fields = ['order_number', 'email', 'first_name', 'last_name', 'phone']
    readonly_fields = ['order_number', 'subtotal', 'delivery_fee', 'total', 'created_at']
    inlines = [OrderItemInline]

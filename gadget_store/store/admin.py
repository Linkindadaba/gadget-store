from django.contrib import admin
from django.shortcuts import render
from .models import Category, Product, ProductImage, Profile


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'discount_price', 'effective_price', 'stock', 'is_featured', 'is_active']
    list_filter = ['category', 'is_featured', 'is_active']
    list_editable = ['price', 'discount_price', 'stock', 'is_featured', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    inlines = [ProductImageInline]
    actions = ['set_discount_percent']
    
    def set_discount_percent(self, request, queryset):
        if 'apply' in request.POST:
            percent = int(request.POST.get('discount_percent', 0))
            for product in queryset:
                if percent > 0:
                    discount = product.price * percent / 100
                    product.discount_price = product.price - discount
                else:
                    product.discount_price = None
                product.save()
            self.message_user(request, f'Discount applied to {queryset.count()} products.')
            return
        return render(request, 'admin/set_discount.html', {
            'products': queryset,
            'title': 'Set Discount Percentage',
        })
    set_discount_percent.short_description = 'Set discount percentage on selected products'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city', 'region']
    search_fields = ['user__username', 'user__email', 'phone']


# Custom admin site
class MyAdminSite(admin.AdminSite):
    site_header = "TechHub Ghana Administration"
    site_title = "TechHub Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        from .models import Product
        from orders.models import Order, OrderItem
        from django.db.models import Sum, Count
        extra_context['total_products'] = Product.objects.count()
        extra_context['total_orders'] = Order.objects.count()
        extra_context['pending_orders'] = Order.objects.filter(status='pending').count()
        extra_context['total_revenue'] = Order.objects.filter(status__in=['paid', 'shipped', 'delivered']).aggregate(Sum('total'))['total__sum'] or 0
        # Status data
        status_counts = Order.objects.values('status').annotate(count=Count('status')).order_by('status')
        status_data = {
            'labels': [dict(Order.STATUS_CHOICES)[s['status']] for s in status_counts],
            'data': [s['count'] for s in status_counts]
        }
        extra_context['status_data'] = status_data
        # Top products
        top_products = OrderItem.objects.values('product_name').annotate(order_count=Sum('quantity')).order_by('-order_count')[:5]
        extra_context['top_products'] = top_products
        # Recent orders
        recent_orders = Order.objects.order_by('-created_at')[:10]
        extra_context['recent_orders'] = recent_orders
        return super().index(request, extra_context)


# Replace the default admin site
admin.site = MyAdminSite()

# Re-register models
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Profile, ProfileAdmin)

# Register Order models
from orders.models import Order, OrderItem
from payments.models import Payment
from django.contrib.auth.models import User, Group

class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'first_name', 'last_name', 'total', 'status', 'created_at']
    list_filter = ['status', 'region']
    search_fields = ['order_number', 'first_name', 'last_name', 'email']

class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'price', 'quantity']

class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'reference', 'amount', 'status', 'paid_at']
    list_filter = ['status']
    search_fields = ['reference', 'order__order_number']

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(User)
admin.site.register(Group)

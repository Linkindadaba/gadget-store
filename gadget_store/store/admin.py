from django.contrib import admin
from django.shortcuts import render, redirect
from django.db.models import Sum, Count
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.core.exceptions import ObjectDoesNotExist
from .models import Category, Product, ProductImage, Profile, Review


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'discount_price', 'effective_price', 'stock', 'is_featured', 'is_active']
    list_filter = ['category', 'is_featured', 'is_active']
    list_editable = ['price', 'discount_price', 'stock', 'is_featured', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    fieldsets = (
        (None, { # This fieldset will contain fields for the main content area
            'fields': (
                'name', 'slug', 'description', 'category',
                'is_featured', 'is_active'
            ),
            'description': 'Basic product details and categorization.',
        }),
        ('Pricing and Inventory', { # This fieldset will contain fields for the sidebar
            'fields': ('price', 'discount_price', 'stock'),
            'description': 'Set product pricing and manage stock levels.',
        }),
        # The 'image' field is handled separately in the custom template for the drop zone
    )
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
            return redirect(request.get_full_path())
        return render(request, 'admin/set_discount.html', {
            'products': queryset,
            'title': 'Set Discount Percentage',
        })
    set_discount_percent.short_description = 'Set discount percentage on selected products'


class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'thumbnail', 'phone', 'city', 'region']
    search_fields = ['user__username', 'user__email', 'phone']

    def thumbnail(self, obj):
        try:
            if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
                return format_html('<img src="{}" style="width: 45px; height:45px; border-radius: 50%; object-fit: cover;" />', obj.profile_picture.url)
        except (AttributeError, ObjectDoesNotExist):
            pass
        return format_html('<div style="width: 45px; height: 45px; border-radius: 50%; background: #eee; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #999;">No Pix</div>')
    thumbnail.short_description = 'Photo'


# Custom admin site
class MyAdminSite(admin.AdminSite):
    site_header = "F.B Nation Administration"
    site_title = "F.B Nation Admin"
    index_title = "Dashboard"

    # Move internal imports here to avoid circular dependencies if models change
    def index(self, request, extra_context=None):
        from orders.models import Order, OrderItem
        extra_context = extra_context or {}
        extra_context['total_products'] = Product.objects.count()
        extra_context['total_orders'] = Order.objects.count()
        extra_context['pending_orders'] = Order.objects.filter(status='pending').count()
        extra_context['total_revenue'] = Order.objects.filter(status__in=['paid', 'shipped', 'delivered']).aggregate(Sum('total'))['total__sum'] or 0
        # Status data
        status_counts = Order.objects.values('status').annotate(count=Count('status')).order_by('status')
        status_data = [
            {
                'label': dict(Order.STATUS_CHOICES).get(s['status'], s['status']),
                'count': s['count'],
            }
            for s in status_counts
        ]
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

# Defined here so it uses the new admin.site
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']

# Register Store models
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Review, ReviewAdmin)

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

# Register remaining models to custom site
from orders.models import Order, OrderItem
from payments.models import Payment
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(User)
admin.site.register(Group)

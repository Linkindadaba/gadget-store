from django.contrib import admin
from django.shortcuts import render, redirect
from django.db.models import Sum, Count, F
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
    list_display = ['name', 'category', 'price', 'discount_price', 'effective_price', 'stock', 'stock_alert', 'is_featured', 'is_active']
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
            'classes': ('two-columns',),
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

    def stock_alert(self, obj):
        if obj.stock <= 5:
            return format_html('<span style="color: #f87171; font-weight: bold;"><i class="bi bi-exclamation-triangle-fill"></i> Low</span>')
        return format_html('<span style="color: #22c55e;"><i class="bi bi-check-circle"></i> OK</span>')
    stock_alert.short_description = 'Status'


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
    site_url = "/"

    # Move internal imports here to avoid circular dependencies if models change
    def index(self, request, extra_context=None):
        from orders.models import Order, OrderItem
        from django.utils import timezone
        import datetime

        extra_context = extra_context or {}

        # Date range filtering
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        order_qs = Order.objects.all()

        if start_date_str:
            try:
                start_date = timezone.make_aware(datetime.datetime.strptime(start_date_str, '%Y-%m-%d'))
                order_qs = order_qs.filter(created_at__gte=start_date)
                extra_context['start_date'] = start_date_str
            except ValueError:
                pass

        if end_date_str:
            try:
                end_date = timezone.make_aware(datetime.datetime.strptime(end_date_str, '%Y-%m-%d'))
                end_date = end_date.replace(hour=23, minute=59, second=59)
                order_qs = order_qs.filter(created_at__lte=end_date)
                extra_context['end_date'] = end_date_str
            except ValueError:
                pass

        extra_context['total_products'] = Product.objects.count()
        extra_context['total_orders'] = order_qs.count()
        extra_context['pending_orders'] = order_qs.filter(status='pending').count()
        extra_context['total_revenue'] = order_qs.filter(status__in=['paid', 'shipped', 'delivered']).aggregate(Sum('total'))['total__sum'] or 0
        
        # Low stock alerts (Threshold: 5)
        low_stock_qs = Product.objects.filter(stock__lte=5, is_active=True)
        extra_context['low_stock_count'] = low_stock_qs.count()
        extra_context['low_stock_list'] = low_stock_qs.order_by('stock')[:5]

        # Status data
        status_counts = order_qs.values('status').annotate(count=Count('status')).order_by('status')
        status_data = [
            {
                'label': dict(Order.STATUS_CHOICES).get(s['status'], s['status']),
                'count': s['count'],
            }
            for s in status_counts
        ]
        extra_context['status_data'] = status_data
        # Top products
        top_products = OrderItem.objects.filter(order__in=order_qs).values('product__name').annotate(product_name=F('product__name'), order_count=Sum('quantity')).order_by('-order_count')[:5]
        extra_context['top_products'] = top_products
        # Recent orders
        recent_orders = order_qs.select_related('user').order_by('-created_at')[:10]
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

# Register remaining models to custom site
from orders.models import Order, OrderItem
from payments.models import Payment
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(User)
admin.site.register(Group)

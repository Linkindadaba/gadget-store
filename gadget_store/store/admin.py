from django.contrib import admin
from django.shortcuts import render, redirect
from django.db import models, transaction
from django.db.models import Sum, Count
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.core.exceptions import ObjectDoesNotExist
from .models import Category, Product, ProductImage, Profile, Review, Wishlist


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'image_preview', 'alt_text']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 80px; width: 80px; object-fit: contain; border-radius: 8px; border: 1px solid #eee;" />', obj.image.url)
        return "-"


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'effective_price', 'stock_display', 'status_toggle', 'is_featured']
    list_filter = ['category', 'is_featured', 'is_active']
    list_editable = ['price', 'is_featured']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    readonly_fields = ['main_image_preview']
    fieldsets = (
        ('Product Information', {
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
        ('Media & Branding', {
            'fields': ('image', 'main_image_preview'),
            'description': 'Upload the primary product image seen in catalogs.',
        }),
    )
    inlines = [ProductImageInline]

    def main_image_preview(self, obj):
        if obj.image:
            return format_html(
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 12px; display: inline-block; border: 2px dashed #dee2e6;">'
                '<img src="{}" style="max-height: 200px; width: auto; display: block;" />'
                '</div>', obj.image.url
            )
        return "No primary image uploaded."
    main_image_preview.short_description = "Preview"

    actions = ['set_discount_percent', 'duplicate_product']

    @transaction.atomic
    def duplicate_product(self, request, queryset):
        for obj in queryset:
            obj.pk = None  # Django creates a new record when PK is None
            obj.slug = f"{obj.slug}-copy-{obj.pk or ''}" # Ensure slug uniqueness
            obj.name = f"COPY: {obj.name}"
            obj.is_active = False # Deactivate clone for safety
            obj.save()
            
        self.message_user(request, f"Successfully duplicated {queryset.count()} products as drafts.")
    duplicate_product.short_description = "Duplicate selected products as drafts"
    
    @transaction.atomic
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

    def stock_display(self, obj):
        if obj.stock <= 5:
            return format_html('<span class="badge bg-danger">Low Stock: {}</span>', obj.stock)
        return format_html('<span class="text-muted">{} in stock</span>', obj.stock)
    stock_display.short_description = 'Inventory'

    def status_toggle(self, obj):
        icon = "check-circle-fill" if obj.is_active else "x-circle"
        color = "success" if obj.is_active else "secondary"
        return format_html('<i class="bi bi-{} text-{}"></i>', icon, color)
    status_toggle.short_description = 'Active'


class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'thumbnail', 'phone', 'city', 'region']
    search_fields = ['user__username', 'user__email', 'phone']

    def thumbnail(self, obj):
        try:
            if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
                return format_html('<img src="{}" class="rounded-circle object-fit-cover" style="width: 45px; height: 45px;" />', obj.profile_picture.url)
        except (AttributeError, ObjectDoesNotExist):
            pass
        return format_html('<div class="rounded-circle bg-light d-flex align-items-center justify-content-center text-muted" style="width: 45px; height: 45px; font-size: 10px;">No Pix</div>')
    thumbnail.short_description = 'Photo'


# Custom admin site
class MyAdminSite(admin.AdminSite):
    site_header = "F.B Nation Administration"
    site_title = "F.B Nation Admin"
    index_title = "Dashboard"

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
        
        # Today's Sales
        today_start = timezone.now().replace(hour=0, minute=0, second=0)
        extra_context['today_sales'] = order_qs.filter(created_at__gte=today_start, status__in=['paid', 'shipped']).aggregate(Sum('total'))['total__sum'] or 0
        
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
        top_products = OrderItem.objects.filter(order__in=order_qs).values('product_name').annotate(order_count=Sum('quantity')).order_by('-order_count')[:5]
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

class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']

# Register Store models
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Review, ReviewAdmin)

class OrderAdmin(admin.ModelAdmin):
    admin.site.register(Wishlist, WishlistAdmin)
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
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(User)
admin.site.register(Group)

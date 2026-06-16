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
    fields = ['image', 'image_preview']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:72px;width:72px;object-fit:contain;'
                'border-radius:8px;border:1px solid #eee;background:#f8f8f8;" />',
                obj.image.url
            )
        return "—"
    image_preview.short_description = "Preview"


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'price', 'effective_price',
        'stock_display', 'status_toggle', 'is_featured',
    ]
    list_filter = ['category', 'is_featured', 'is_active']
    list_editable = ['price', 'is_featured']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    # 'image' is rendered by the custom change_form.html drop zone — NOT in fieldsets.
    # Listing it here would render it twice.
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'slug', 'description', 'category', 'is_featured', 'is_active'),
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'discount_price', 'stock'),
        }),
    )
    inlines = [ProductImageInline]

    actions = ['set_discount_percent', 'duplicate_product']

    def stock_display(self, obj):
        if obj.stock == 0:
            return format_html('<span style="color:#dc3545;font-weight:600;">Out of Stock</span>')
        if obj.stock <= 5:
            return format_html('<span style="color:#fd7e14;font-weight:600;">Low: {}</span>', obj.stock)
        return format_html('<span style="color:#198754;">{} in stock</span>', obj.stock)
    stock_display.short_description = 'Stock'

    def status_toggle(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#198754;font-weight:600;">● Active</span>')
        return format_html('<span style="color:#adb5bd;font-weight:600;">○ Draft</span>')
    status_toggle.short_description = 'Status'

    @transaction.atomic
    def duplicate_product(self, request, queryset):
        for obj in queryset:
            original_slug = obj.slug
            obj.pk = None
            obj.slug = f"{original_slug}-copy"
            obj.name = f"COPY: {obj.name}"
            obj.is_active = False
            obj.save()
        self.message_user(request, f"Duplicated {queryset.count()} product(s) as drafts.")
    duplicate_product.short_description = "Duplicate selected products as drafts"

    @transaction.atomic
    def set_discount_percent(self, request, queryset):
        if 'apply' in request.POST:
            percent = int(request.POST.get('discount_percent', 0))
            for product in queryset:
                if percent > 0:
                    product.discount_price = round(product.price * (1 - percent / 100), 2)
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
                return format_html(
                    '<img src="{}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;" />',
                    obj.profile_picture.url
                )
        except (AttributeError, ObjectDoesNotExist):
            pass
        return format_html(
            '<div style="width:40px;height:40px;border-radius:50%;background:#eee;'
            'display:flex;align-items:center;justify-content:center;font-size:11px;color:#aaa;">—</div>'
        )
    thumbnail.short_description = 'Photo'


class MyAdminSite(admin.AdminSite):
    site_header = "F.B Nation Administration"
    site_title = "F.B Nation Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        from orders.models import Order, OrderItem
        from django.utils import timezone
        import datetime

        extra_context = extra_context or {}

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

        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        extra_context['total_products'] = Product.objects.count()
        extra_context['total_orders'] = order_qs.count()
        extra_context['pending_orders'] = order_qs.filter(status='pending').count()
        extra_context['today_sales'] = (
            order_qs.filter(created_at__gte=today_start, status__in=['paid', 'shipped'])
            .aggregate(Sum('total'))['total__sum'] or 0
        )
        extra_context['total_revenue'] = (
            order_qs.filter(status__in=['paid', 'shipped', 'delivered'])
            .aggregate(Sum('total'))['total__sum'] or 0
        )

        low_stock_qs = Product.objects.filter(stock__lte=5, is_active=True)
        extra_context['low_stock_count'] = low_stock_qs.count()
        extra_context['low_stock_list'] = low_stock_qs.order_by('stock')[:5]

        status_counts = (
            order_qs.values('status').annotate(count=Count('status')).order_by('status')
        )
        extra_context['status_data'] = [
            {'label': dict(Order.STATUS_CHOICES).get(s['status'], s['status']), 'count': s['count']}
            for s in status_counts
        ]
        extra_context['top_products'] = (
            OrderItem.objects.filter(order__in=order_qs)
            .values('product_name').annotate(order_count=Sum('quantity'))
            .order_by('-order_count')[:5]
        )
        extra_context['recent_orders'] = (
            order_qs.select_related('user').order_by('-created_at')[:10]
        )
        return super().index(request, extra_context)


# Replace the default admin site
admin.site = MyAdminSite()


class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']


class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']


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


# ── Register all models ────────────────────────────────────────────────────────
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Wishlist, WishlistAdmin)
admin.site.register(User)
admin.site.register(Group)

from orders.models import Order, OrderItem
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)

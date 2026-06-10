from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

from .auth_views import RateLimitedLoginView, RateLimitedPasswordResetView, RateLimitedPasswordResetConfirmView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
    path('orders/', include('orders.urls')),
    path('payments/', include('payments.urls')),
    path('logistics/', include('logistics.urls')),
    # Override sensitive auth endpoints with rate-limited views
    path('accounts/login/', RateLimitedLoginView.as_view(), name='login'),
    path('accounts/password_reset/', RateLimitedPasswordResetView.as_view(), name='password_reset'),
    path('accounts/reset/<uidb64>/<token>/', RateLimitedPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/', include('django.contrib.auth.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve local media when using FileSystemStorage in containers or production.
if settings.STORAGES.get('default', {}).get('BACKEND', '') == 'django.core.files.storage.FileSystemStorage':
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

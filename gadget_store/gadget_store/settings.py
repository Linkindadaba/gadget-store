from pathlib import Path
import os
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production-use-env-vars')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='gadget-store-production-280d.up.railway.app,localhost,127.0.0.1').split(',')

# CSRF settings for production
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host not in ['localhost', '127.0.0.1']]

# Production Security Settings
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'cloudinary_storage',
    'cloudinary',
    'store',
    'orders',
    'payments',
    'logistics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For serving static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gadget_store.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.social_media_links',
                'store.context_processors.cart_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'gadget_store.wsgi.application'

# Database configuration - uses PostgreSQL on Railway, SQLite locally
if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.config(
            default='sqlite:///db.sqlite3',
            conn_max_age=600,
            conn_health_checks=True,
        )
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Accra'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudinary Storage Configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Payment settings (Flutterwave)
FLUTTERWAVE_SECRET_KEY = config('FLUTTERWAVE_SECRET_KEY', default='FLWSECK_TEST-XXXXXXXXXXXXXXXX-X') # IMPORTANT: Replace with your actual Secret Key
FLUTTERWAVE_ENCRYPTION_KEY = config('FLUTTERWAVE_ENCRYPTION_KEY', default='UO9BOWQpvWbd1rY+Qs2+IzLhhHrwoqfAnD+h/SwQqOQ=')
FLUTTERWAVE_WEBHOOK_SECRET = config('FLUTTERWAVE_WEBHOOK_SECRET', default='your_flutterwave_webhook_secret') # IMPORTANT: Change this default!
FLUTTERWAVE_CURRENCY = 'GHS' # Assuming Ghana Cedi

# Delivery fee settings (in GHS)
DELIVERY_REGIONS = {
    'Greater Accra': 15.00,
    'Ashanti': 35.00,
    'Western': 45.00,
    'Eastern': 30.00,
    'Central': 40.00,
    'Volta': 50.00,
    'Northern': 70.00,
    'Upper East': 80.00,
    'Upper West': 80.00,
    'Brong-Ahafo': 55.00,
    'Bono East': 55.00,
    'Ahafo': 55.00,
    'Savannah': 75.00,
    'North East': 78.00,
    'Oti': 60.00,
    'Western North': 50.00,
}

# Ensure auth form inputs have Bootstrap styling
from django import forms

# Social Media Handles
SOCIAL_MEDIA = {
    'facebook': config('SOCIAL_FB', default='https://facebook.com/fbnation'),
    'instagram': config('SOCIAL_INSTA', default='https://instagram.com/fbnation'),
    'twitter': config('SOCIAL_TWITTER', default='https://x.com/fbnation'),
    'tiktok': config('SOCIAL_TIKTOK', default='https://tiktok.com/@fbnation'),
}

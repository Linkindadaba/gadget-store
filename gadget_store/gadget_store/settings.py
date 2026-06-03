from pathlib import Path
import os
from decouple import config
import dj_database_url
import cloudinary
from django.core.exceptions import ImproperlyConfigured
import logging
import logging.config

BASE_DIR = Path(__file__).resolve().parent.parent
# Security: require SECRET_KEY in environment for predictable behavior in production
SECRET_KEY = config('SECRET_KEY', default=None)
if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY environment variable is required and must not be empty.')

# Default to safe production setting. Development machines should explicitly opt-in with DEBUG=True.
DEBUG = config('DEBUG', default=False, cast=bool)

# ALLOWED_HOSTS should be set explicitly. Empty list is safest default.
ALLOWED_HOSTS = [host.strip() for host in config('ALLOWED_HOSTS', default='').split(',') if host.strip()]

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
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',
    'crispy_forms',
    'crispy_bootstrap5',
    'store',
    'orders',
    'payments',
    'logistics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
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

# Database configuration
# Use PostgreSQL whenever DATABASE_URL is configured.
# Fall back to local SQLite only when DEBUG=True and DATABASE_URL is not set.
DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    if not DEBUG:
        raise ImproperlyConfigured(
            'DATABASE_URL must be set when DEBUG=False. '
            'Set the Railway environment variable to your PostgreSQL URL.'
        )
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
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

# Cloudinary Configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

# Storage Configuration (Django 4.2+)
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage" 
        if CLOUDINARY_STORAGE['CLOUD_NAME'] else "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cache backend used by Django for session and other caching needs.
# django-ratelimit decorators work without installing the app entry.
# Redis is recommended for production to share rate-limit state across workers.
if config('REDIS_URL', default=''):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": config('REDIS_URL'),
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# Log database configuration for debugging (shown in Railway logs)
import sys
_db_engine = DATABASES['default'].get('ENGINE', 'unknown')
_db_host = DATABASES['default'].get('HOST', 'N/A')

sys.stderr.write(f"--- [Django Startup] ---\n")
sys.stderr.write(f"Mode: {'Production' if not DEBUG else 'Development'}\n")
sys.stderr.write(f"DB Engine: {_db_engine}\n")
sys.stderr.write(f"DB Host: {_db_host}\n")
sys.stderr.write(f"------------------------\n")

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Payment settings (Flutterwave)
FLUTTERWAVE_SECRET_KEY = config('FLUTTERWAVE_SECRET_KEY', default=None)
FLUTTERWAVE_ENCRYPTION_KEY = config('FLUTTERWAVE_ENCRYPTION_KEY', default=None)
FLUTTERWAVE_WEBHOOK_SECRET = config('FLUTTERWAVE_WEBHOOK_SECRET', default=None)
FLUTTERWAVE_CURRENCY = config('FLUTTERWAVE_CURRENCY', default='GHS')
FLUTTERWAVE_MOBILE_MONEY_NETWORKS = [
    ('MTN', 'MTN Mobile Money'),
    ('VODAFONE', 'Vodafone Cash'),
    ('AIRTELTIGO', 'AirtelTigo Money'),
]

# Payment settings (Paystack)
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default=None)
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default=None)
PAYSTACK_WEBHOOK_SECRET = config('PAYSTACK_WEBHOOK_SECRET', default=None)
PAYSTACK_ALLOWED_IPS = [ip.strip() for ip in config('PAYSTACK_ALLOWED_IPS', default='').split(',') if ip.strip()]
PAYSTACK_CURRENCY = config('PAYSTACK_CURRENCY', default='GHS')

# Enforce required payment secrets in production; allow test placeholders only when DEBUG=True
if not DEBUG:
    if not PAYSTACK_SECRET_KEY:
        raise ImproperlyConfigured('PAYSTACK_SECRET_KEY must be set in production as an environment variable.')
    if not FLUTTERWAVE_SECRET_KEY:
        raise ImproperlyConfigured('FLUTTERWAVE_SECRET_KEY must be set in production as an environment variable.')
else:
    # Provide non-sensitive test placeholders for local development to avoid crashes.
    PAYSTACK_SECRET_KEY = PAYSTACK_SECRET_KEY or 'sk_test_PLACEHOLDER'
    PAYSTACK_PUBLIC_KEY = PAYSTACK_PUBLIC_KEY or 'pk_test_PLACEHOLDER'
    PAYSTACK_WEBHOOK_SECRET = PAYSTACK_WEBHOOK_SECRET or 'webhook_test_placeholder'
    FLUTTERWAVE_SECRET_KEY = FLUTTERWAVE_SECRET_KEY or 'FLWSECK_TEST_PLACEHOLDER'
    FLUTTERWAVE_ENCRYPTION_KEY = FLUTTERWAVE_ENCRYPTION_KEY or 'ENCRYPTION_KEY_PLACEHOLDER'
    FLUTTERWAVE_WEBHOOK_SECRET = FLUTTERWAVE_WEBHOOK_SECRET or 'webhook_test_placeholder'

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

# CORS configuration (use strict origins in production)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS if host not in ['localhost', '127.0.0.1']
]

# Email / Password reset security
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='webmaster@localhost')
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
PASSWORD_RESET_TIMEOUT = config('PASSWORD_RESET_TIMEOUT', default=3600, cast=int)  # seconds

# Basic logging configuration
LOG_LEVEL = config('LOG_LEVEL', default='INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
}

# Optional Sentry integration for alerts (configure SENTRY_DSN in env)
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(dsn=SENTRY_DSN, integrations=[DjangoIntegration()], traces_sample_rate=0.0)
    except Exception:
        # Don't fail startup if Sentry isn't available
        logging.getLogger(__name__).exception('Failed to initialize Sentry')

# Rate limiting defaults (use django-ratelimit decorators or middleware per-view)
RATE_LIMIT_DEFAULT = config('RATE_LIMIT_DEFAULT', default='100/h')

# Social Media Handles
SOCIAL_MEDIA = {
    'facebook': config('SOCIAL_FB', default='https://facebook.com/fbnation'),
    'instagram': config('SOCIAL_INSTA', default='https://instagram.com/fbnation'),
    'twitter': config('SOCIAL_TWITTER', default='https://x.com/fbnation'),
    'tiktok': config('SOCIAL_TIKTOK', default='https://tiktok.com/@fbnation'),
}

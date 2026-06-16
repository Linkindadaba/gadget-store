from pathlib import Path
import os
import sys
from decouple import config
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
import logging
import logging.config

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = config('DEBUG', default=False, cast=bool)

SECRET_KEY = config('SECRET_KEY', default=None)
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-secret-key-change-me'
    else:
        raise ImproperlyConfigured('SECRET_KEY environment variable is required and must not be empty when DEBUG=False.')

# ── Cloudinary (read early so INSTALLED_APPS can branch on it) ─────────────────
CLOUDINARY_CLOUD_NAME = config('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}
USE_CLOUDINARY = bool(CLOUDINARY_CLOUD_NAME)

# ── Allowed Hosts ──────────────────────────────────────────────────────────────
ALLOWED_HOSTS = [
    h.strip() for h in config('ALLOWED_HOSTS', default='').split(',') if h.strip()
]
_replit_domain = os.environ.get('REPLIT_DEV_DOMAIN', '')
if _replit_domain and _replit_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_replit_domain)
if DEBUG:
    ALLOWED_HOSTS = ['*']

# ── CSRF trusted origins ───────────────────────────────────────────────────────
# Priority 1: explicit env var — set this in Railway as a comma-separated list
# e.g. CSRF_TRUSTED_ORIGINS=https://gadget-store-production-280d.up.railway.app
_csrf_explicit = config('CSRF_TRUSTED_ORIGINS', default='')
if _csrf_explicit:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_explicit.split(',') if o.strip()]
else:
    # Priority 2: derive from ALLOWED_HOSTS + known platform domains
    _csrf_hosts = [
        h.strip() for h in config('ALLOWED_HOSTS', default='').split(',')
        if h.strip() and h.strip() not in ('localhost', '127.0.0.1', '*')
    ]
    if _replit_domain:
        _csrf_hosts.append(_replit_domain)
    # Railway sets RAILWAY_PUBLIC_DOMAIN automatically
    for _env_key in ('RAILWAY_PUBLIC_DOMAIN', 'RAILWAY_STATIC_URL', 'RAILWAY_SERVICE_DOMAIN'):
        _rdomain = os.environ.get(_env_key, '').strip().lstrip('https://').rstrip('/')
        if _rdomain and _rdomain not in _csrf_hosts:
            _csrf_hosts.append(_rdomain)
    CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in _csrf_hosts]

if DEBUG:
    CSRF_TRUSTED_ORIGINS += ['http://localhost:5000', 'http://127.0.0.1:5000']

# ── Production security ────────────────────────────────────────────────────────
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ── Installed Apps ─────────────────────────────────────────────────────────────
# IMPORTANT: django.contrib.staticfiles MUST appear before cloudinary_storage.
# Django resolves management commands by iterating INSTALLED_APPS in reverse;
# whichever app appears FIRST wins.  Putting cloudinary_storage first caused it
# to shadow Django's own collectstatic, resulting in 0 files copied.
INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',   # ← must be before cloudinary_storage
    'crispy_forms',
    'crispy_bootstrap5',
    'store',
    'orders',
    'payments',
    'logistics',
]
if USE_CLOUDINARY:
    INSTALLED_APPS += ['cloudinary_storage', 'cloudinary']

# ── Middleware ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
                'store.context_processors.categories',
                'store.context_processors.support_contacts',
            ],
        },
    },
]

WSGI_APPLICATION = 'gadget_store.wsgi.application'

# ── Database ───────────────────────────────────────────────────────────────────
DATABASE_URL = config('DATABASE_URL', default='')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, conn_health_checks=True)
    }
else:
    if not DEBUG:
        raise ImproperlyConfigured('DATABASE_URL must be set when DEBUG=False.')
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

# ── Static files ───────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Storage backends
STORAGES = {
    "default": {
        "BACKEND": (
            "cloudinary_storage.storage.MediaCloudinaryStorage"
            if USE_CLOUDINARY
            else "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        # CompressedStaticFilesStorage gives gzip compression without hashed
        # filenames; safe for production and works without a manifest file.
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Compat shim — some third-party packages still read STATICFILES_STORAGE
STATICFILES_STORAGE = STORAGES["staticfiles"]["BACKEND"]

WHITENOISE_MANIFEST_STRICT = False
# Use finders only in DEBUG mode (dev server); in production files come from STATIC_ROOT
WHITENOISE_USE_FINDERS = DEBUG

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Cache ──────────────────────────────────────────────────────────────────────
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

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

# ── Celery ─────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-orders-hourly': {
        'task': 'orders.tasks.cleanup_expired_orders',
        'schedule': 3600.0,
    },
}

# ── Startup log ────────────────────────────────────────────────────────────────
_db_engine = DATABASES['default'].get('ENGINE', 'unknown')
_db_host = DATABASES['default'].get('HOST', 'N/A')
sys.stderr.write(f"--- [Django Startup] ---\n")
sys.stderr.write(f"Mode: {'Production' if not DEBUG else 'Development'}\n")
sys.stderr.write(f"DB Engine: {_db_engine}\n")
sys.stderr.write(f"DB Host: {_db_host}\n")
sys.stderr.write(f"------------------------\n")

# ── Crispy Forms ───────────────────────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ── Auth ───────────────────────────────────────────────────────────────────────
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ── Payments ───────────────────────────────────────────────────────────────────
FLUTTERWAVE_SECRET_KEY = config('FLUTTERWAVE_SECRET_KEY', default=None)
FLUTTERWAVE_ENCRYPTION_KEY = config('FLUTTERWAVE_ENCRYPTION_KEY', default=None)
FLUTTERWAVE_WEBHOOK_SECRET = config('FLUTTERWAVE_WEBHOOK_SECRET', default=None)
FLUTTERWAVE_CURRENCY = config('FLUTTERWAVE_CURRENCY', default='GHS')
FLUTTERWAVE_MOBILE_MONEY_NETWORKS = [
    ('MTN', 'MTN Mobile Money'),
    ('VODAFONE', 'Vodafone Cash'),
    ('AIRTELTIGO', 'AirtelTigo Money'),
]

PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default=None)
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default=None)
PAYSTACK_WEBHOOK_SECRET = config('PAYSTACK_WEBHOOK_SECRET', default=None)
PAYSTACK_ALLOWED_IPS = [ip.strip() for ip in config('PAYSTACK_ALLOWED_IPS', default='').split(',') if ip.strip()]
PAYSTACK_CURRENCY = config('PAYSTACK_CURRENCY', default='GHS')

if not DEBUG:
    if not PAYSTACK_SECRET_KEY:
        raise ImproperlyConfigured('PAYSTACK_SECRET_KEY must be set in production.')
    if not FLUTTERWAVE_SECRET_KEY:
        raise ImproperlyConfigured('FLUTTERWAVE_SECRET_KEY must be set in production.')
else:
    PAYSTACK_SECRET_KEY = PAYSTACK_SECRET_KEY or 'sk_test_PLACEHOLDER'
    PAYSTACK_PUBLIC_KEY = PAYSTACK_PUBLIC_KEY or 'pk_test_PLACEHOLDER'
    PAYSTACK_WEBHOOK_SECRET = PAYSTACK_WEBHOOK_SECRET or 'webhook_test_placeholder'
    FLUTTERWAVE_SECRET_KEY = FLUTTERWAVE_SECRET_KEY or 'FLWSECK_TEST_PLACEHOLDER'
    FLUTTERWAVE_ENCRYPTION_KEY = FLUTTERWAVE_ENCRYPTION_KEY or 'ENCRYPTION_KEY_PLACEHOLDER'
    FLUTTERWAVE_WEBHOOK_SECRET = FLUTTERWAVE_WEBHOOK_SECRET or 'webhook_test_placeholder'

# ── Delivery regions ───────────────────────────────────────────────────────────
DELIVERY_REGIONS = {
    'Greater Accra': 15.00, 'Ashanti': 35.00, 'Western': 45.00,
    'Eastern': 30.00, 'Central': 40.00, 'Volta': 50.00,
    'Northern': 70.00, 'Upper East': 80.00, 'Upper West': 80.00,
    'Brong-Ahafo': 55.00, 'Bono East': 55.00, 'Ahafo': 55.00,
    'Savannah': 75.00, 'North East': 78.00, 'Oti': 60.00, 'Western North': 50.00,
}

# ── CORS ───────────────────────────────────────────────────────────────────────
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    f"https://{h}" for h in (
        h.strip() for h in config('ALLOWED_HOSTS', default='').split(',')
        if h.strip() and h.strip() not in ('localhost', '127.0.0.1', '*')
    )
]
if DEBUG:
    CORS_ALLOWED_ORIGINS.extend(['http://localhost:8000', 'http://127.0.0.1:8000'])

# ── Email ──────────────────────────────────────────────────────────────────────
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='webmaster@localhost')
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
PASSWORD_RESET_TIMEOUT = config('PASSWORD_RESET_TIMEOUT', default=3600, cast=int)

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_LEVEL = config('LOG_LEVEL', default='INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s'},
    },
    'handlers': {
        'console': {'level': LOG_LEVEL, 'class': 'logging.StreamHandler', 'formatter': 'standard'},
    },
    'root': {'handlers': ['console'], 'level': LOG_LEVEL},
}

# ── Sentry (optional) ──────────────────────────────────────────────────────────
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        sentry_sdk.init(dsn=SENTRY_DSN, integrations=[DjangoIntegration()], traces_sample_rate=0.0)
    except Exception:
        logging.getLogger(__name__).exception('Failed to initialize Sentry')

RATE_LIMIT_DEFAULT = config('RATE_LIMIT_DEFAULT', default='100/h')

# ── Social media & support ─────────────────────────────────────────────────────
SOCIAL_MEDIA = {
    'facebook': config('SOCIAL_FB', default='https://facebook.com/fbnation'),
    'instagram': config('SOCIAL_INSTA', default='https://instagram.com/fbnation'),
    'twitter': config('SOCIAL_TWITTER', default='https://x.com/fbnation'),
    'tiktok': config('SOCIAL_TIKTOK', default='https://www.tiktok.com/@felixbani00?_r=1&_t=ZS-966GeMXj9Gf'),
}

SUPPORT_CONTACTS = {
    'developer': {
        'email': config('DEV_EMAIL', default='sikapalinkz@gmail.com'),
        'whatsapp': config('DEV_WHATSAPP', default='233557185634'),
    },
    'client': {
        'email': config('CLIENT_EMAIL', default='felixejike2004@gmail.com'),
        'whatsapp': config('CLIENT_WHATSAPP', default='+233 50 878 7783'),
        'tiktok': config('CLIENT_TIKTOK', default='https://www.tiktok.com/@felixbani00?_r=1&_t=ZS-966GeMXj9Gf'),
    }
}

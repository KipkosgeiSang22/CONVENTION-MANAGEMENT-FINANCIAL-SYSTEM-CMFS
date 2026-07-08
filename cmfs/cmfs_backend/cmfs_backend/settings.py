from decouple import config, Csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('DJANGO_SECRET_KEY')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    'django_q',
    # Local apps
    'auth_app',
    'conventions',
    'budget',
    'delegates',
    'payments',
    'gate',
    'reports',
    'django_ratelimit',

]
SILENCED_SYSTEM_CHECKS = ['django_ratelimit.E003', 'django_ratelimit.W001']
#silces the error caused by django, it doesn't allow  locmem.LocMemCache to work in production but works in development
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'payments.middleware.MpesaIPWhitelistMiddleware', 
    'auth_app.middleware.JWTAuthMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'cmfs_backend.middleware.csp.CSPMiddleware',
]

ROOT_URLCONF = 'cmfs_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cmfs_backend.wsgi.application'

import dj_database_url
DATABASE_URL = config('DATABASE_URL')
DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000', cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# DRF
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
    'EXCEPTION_HANDLER': 'cmfs_backend.utils.exceptions.custom_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
}

# Django Q2 — PostgreSQL broker, no Redis
Q_CLUSTER = {
    'name': 'cmfs',
    'workers': 2,
    'recycle': 500,
    'timeout': 60,
    'retry': 120,
    'queue_limit': 50,
    'bulk': 10,
    'orm': 'default',
}

# Email
RESEND_API_KEY = config('RESEND_API_KEY', default='')

# SMS (Super Admin critical alerts only)
AFRICA_TALKING_USERNAME = config('AFRICA_TALKING_USERNAME', default='')
AFRICA_TALKING_API_KEY = config('AFRICA_TALKING_API_KEY', default='')

# M-Pesa
MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY', default='')
MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET', default='')
MPESA_SHORTCODE = config('MPESA_SHORTCODE', default='')
MPESA_PASSKEY = config('MPESA_PASSKEY', default='')
MPESA_CALLBACK_URL = config('MPESA_CALLBACK_URL', default='')
MPESA_IP_WHITELIST = config(
    'MPESA_IP_WHITELIST',
    default='196.201.214.200,196.201.214.206,196.201.213.114,196.201.214.207,'
            '196.201.214.208,196.201.213.44,196.201.212.127,196.201.212.138,'
            '196.201.212.129,196.201.212.136,196.201.212.74,196.201.212.69',
    cast=Csv(),
)
MPESA_BASE_URL = config('MPESA_BASE_URL', default='https://sandbox.safaricom.co.ke')
MPESA_CALLBACK_HMAC_SECRET = config('MPESA_CALLBACK_HMAC_SECRET', default=MPESA_PASSKEY)


# JWT
JWT_SECRET_KEY = config('JWT_SECRET_KEY')
JWT_ACCESS_TOKEN_EXPIRY_MINUTES = 15
JWT_REFRESH_TOKEN_EXPIRY_DAYS = 7

# Frontend
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'ratelimit-cache',
    }
}
RATELIMIT_USE_CACHE = 'default'
#TODO switch to redis or memchached in production
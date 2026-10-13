"""Runtime-only client settings. Production defaults fail closed."""
import os
from pathlib import Path
from urllib.parse import urlparse, unquote,parse_qs
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG = ENVIRONMENT == 'development'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'development-only-not-for-production-change-me')
if not DEBUG and (not os.getenv('DJANGO_SECRET_KEY') or len(SECRET_KEY) < 40):
    raise ImproperlyConfigured('Production requires a unique DJANGO_SECRET_KEY of at least 40 characters.')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
CSRF_TRUSTED_ORIGINS = [x for x in os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:3000,http://localhost:3001').split(',') if x]
INSTALLED_APPS = [
    'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
    'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'drf_spectacular',
    'apps.identity', 'apps.configuration', 'apps.catalog', 'apps.inventory',
    'apps.delivery', 'apps.promotions', 'apps.orders', 'apps.payments',
    'apps.imports', 'apps.content', 'apps.customers', 'apps.analytics', 'apps.operations',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.identity.middleware.SessionLifetimeMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
AUTH_USER_MODEL = 'identity.User'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
db = os.getenv('DATABASE_URL', '')
if db:
    u = urlparse(db)
    if u.scheme not in ['postgres','postgresql']:raise ImproperlyConfigured('DATABASE_URL must use PostgreSQL.')
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': u.path.lstrip('/'),
        'USER': unquote(u.username or ''), 'PASSWORD': unquote(u.password or ''),
        'HOST': u.hostname, 'PORT': u.port or 5432, 'CONN_MAX_AGE': 60,
        'OPTIONS':{k:v[0] for k,v in parse_qs(u.query).items() if k in ['sslmode','sslrootcert','connect_timeout']}}}
elif DEBUG:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.getenv('SQLITE_PATH', str(BASE_DIR / 'development.sqlite3'))}}
else:
    raise ImproperlyConfigured('Production requires PostgreSQL DATABASE_URL.')
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]
LANGUAGE_CODE = 'en'
LANGUAGES = [('en', 'English'), ('ar', 'العربية')]
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT', BASE_DIR / 'media'))
MEDIA_URL = '/media/'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
DATA_UPLOAD_MAX_MEMORY_SIZE = 11 * 1024 * 1024
REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES':['common.parsers.ObjectJSONParser','rest_framework.parsers.FormParser','rest_framework.parsers.MultiPartParser'],
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_SCHEMA_CLASS': 'config.schema.RetailSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 30,
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle', 'rest_framework.throttling.UserRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'anon': '300/hour', 'user': '3000/hour', 'auth': '15/hour'},
    'EXCEPTION_HANDLER': 'common.api.exception_handler',
}
SPECTACULAR_SETTINGS = {'TITLE': 'Reusable Retail Backend API', 'VERSION': '0.3.0', 'SERVE_INCLUDE_SCHEMA': False,
    'PREPROCESSING_HOOKS':['config.schema.implemented_methods']}
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@localhost')
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_BEAT_SCHEDULE = {'expire-orders': {'task': 'apps.orders.tasks.expire_orders', 'schedule': 60.0}}
if os.getenv('REDIS_URL'):
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': os.environ['REDIS_URL']}}
FIELD_ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY', '')
ANALYTICS_TEST_DEPLOYMENT = os.getenv('ANALYTICS_TEST_DEPLOYMENT','false').lower()=='true'
CARD_ENABLED = os.getenv('CARD_ENABLED','false').lower()=='true'
CARD_PROVIDER = os.getenv('CARD_PROVIDER','skipcash')
PAYMENT_RETURN_URL = os.getenv('PAYMENT_RETURN_URL','')
SKIPCASH_ENV = os.getenv('SKIPCASH_ENV','sandbox')
SKIPCASH_CLIENT_ID = os.getenv('SKIPCASH_CLIENT_ID','')
SKIPCASH_KEY_ID = os.getenv('SKIPCASH_KEY_ID','')
SKIPCASH_KEY_SECRET = os.getenv('SKIPCASH_KEY_SECRET','')
SKIPCASH_WEBHOOK_KEY = os.getenv('SKIPCASH_WEBHOOK_KEY','')
SKIPCASH_CHECKOUT_HOSTS = [x.strip() for x in os.getenv('SKIPCASH_CHECKOUT_HOSTS','skipcashtest.azurewebsites.net,api.skipcash.app,pay.skipcash.app').split(',') if x.strip()]
CELERY_BEAT_SCHEDULE['reconcile-card']={'task':'apps.payments.tasks.reconcile_pending_payments','schedule':60.0}
if SKIPCASH_ENV not in ['sandbox','production']:raise ImproperlyConfigured('SKIPCASH_ENV must be sandbox or production.')
if not DEBUG:
    if not FIELD_ENCRYPTION_KEY:raise ImproperlyConfigured('Production requires an independent FIELD_ENCRYPTION_KEY.')
    if not os.getenv('REDIS_URL'):raise ImproperlyConfigured('Production requires Redis for shared throttles and background tasks.')
    if CARD_ENABLED and (not all([SKIPCASH_CLIENT_ID,SKIPCASH_KEY_ID,SKIPCASH_KEY_SECRET,SKIPCASH_WEBHOOK_KEY]) or not PAYMENT_RETURN_URL.startswith('https://')):
        raise ImproperlyConfigured('Enabled card payment requires credentials and an HTTPS return URL.')
    if ENVIRONMENT=='production' and CARD_ENABLED and SKIPCASH_ENV!='production':raise ImproperlyConfigured('Production card payment cannot use the sandbox gateway.')
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SESSION_COOKIE_NAME = os.getenv('SESSION_COOKIE_NAME','retail_session')
CSRF_COOKIE_NAME = os.getenv('CSRF_COOKIE_NAME','retail_csrf')
PASSWORD_RESET_TIMEOUT = 900
CUSTOMER_ORIGIN = os.getenv('CUSTOMER_ORIGIN','').rstrip('/')
EMAIL_TIMEOUT = 20
NOTIFICATION_MESSAGE_ID_DOMAIN = os.getenv('NOTIFICATION_MESSAGE_ID_DOMAIN','retail.invalid')
CELERY_BEAT_SCHEDULE['deliver-outbox']={'task':'apps.operations.tasks.deliver_outbox','schedule':30.0}
if CUSTOMER_ORIGIN and (urlparse(CUSTOMER_ORIGIN).scheme!='https' and not DEBUG):raise ImproperlyConfigured('CUSTOMER_ORIGIN must use HTTPS in production.')

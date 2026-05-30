"""
Django settings for ReDIB COA portal.
"""

from pathlib import Path
import os
import environ
from django.contrib.messages import constants as message_constants

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False)
)

# Read .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# CSRF trusted origins (required for HTTPS behind reverse proxy)
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Required for allauth

    # Wagtail (marketing site CMS) + bilingual content
    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail',
    'modelcluster',
    'taggit',
    'wagtail_localize',
    'wagtail_localize.locales',

    # Third-party apps
    'rest_framework',
    'django_htmx',
    'crispy_forms',
    'crispy_bootstrap5',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'simple_history',

    # Local apps
    'core',
    'calls',
    'applications',
    'evaluations',
    'access',
    'communications',
    'reports',
    'newsletters',

    # Marketing site (Wagtail page models)
    'home',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.middleware.ProfileCompletionMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',  # HTMX support
    'simple_history.middleware.HistoryRequestMiddleware',  # Audit trail
    'allauth.account.middleware.AccountMiddleware',  # Required for django-allauth
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',  # Wagtail redirects (must be last)
]

ROOT_URLCONF = 'redib.urls'

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
                'django.template.context_processors.media',
                'core.context_processors.contact_email',
                'core.context_processors.user_roles',
            ],
        },
    },
]

WSGI_APPLICATION = 'redib.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
}

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization — bilingual marketing site, Spanish default
LANGUAGE_CODE = 'es'
TIME_ZONE = 'Europe/Madrid'  # Spain timezone for ReDIB
USE_I18N = True
USE_TZ = True

# Wagtail bilingual config (human translation only — no machine-translate backend).
# Per-page slug aliases at the root, not /es/ /en/ URL prefixes — do NOT use i18n_patterns.
WAGTAIL_I18N_ENABLED = True
WAGTAIL_CONTENT_LANGUAGES = [
    ('es', 'Español'),
    ('en', 'English'),
]
LANGUAGES = WAGTAIL_CONTENT_LANGUAGES

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Site ID (required for django-allauth)
SITE_ID = 1

# Django-allauth configuration (updated to django-allauth 0.58+ API)
ACCOUNT_LOGIN_METHODS = {'email'}  # Use email for authentication (replaces ACCOUNT_AUTHENTICATION_METHOD)
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_SIGNUP_FIELDS = [
    'email*',     # Email required
    'email2*',    # Email confirmation required (replaces ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE)
    'password1*', # Password required
    'password2*', # Password confirmation required
]
# Note: Username not included in ACCOUNT_SIGNUP_FIELDS (replaces ACCOUNT_USERNAME_REQUIRED=False)
# Note: Email required via email* in ACCOUNT_SIGNUP_FIELDS (replaces ACCOUNT_EMAIL_REQUIRED=True)
LOGIN_REDIRECT_URL = '/portal/'
LOGOUT_REDIRECT_URL = '/portal/'

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Map Django message levels to Bootstrap alert classes.
# Django uses 'error' but Bootstrap uses 'danger', so we override the mapping
# so that messages.error() renders as alert-danger (red).
MESSAGE_TAGS = {
    message_constants.ERROR: 'danger',
}

# Email Configuration
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@redib.net')
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
if EMAIL_BACKEND != 'django.core.mail.backends.console.EmailBackend':
    EMAIL_HOST = env('EMAIL_HOST', default='smtp.ionos.es')
    EMAIL_PORT = env.int('EMAIL_PORT', default=587)
    EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
    EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
CONTACT_EMAIL = env('CONTACT_EMAIL', default='info@redib.net')

# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# In development (DEBUG=True) or when running the test runner, execute Celery
# tasks synchronously in-process. Tests run with DEBUG=False but still need
# eager execution so mail.outbox captures outgoing workflow emails and tests
# aren't silently broken by an absent broker. In production neither flag is
# set so .delay() queues to the real broker normally.
import sys as _sys
_IS_TESTING = 'test' in _sys.argv or 'pytest' in _sys.argv[0]
CELERY_TASK_ALWAYS_EAGER = DEBUG or _IS_TESTING
CELERY_TASK_EAGER_PROPAGATES = DEBUG or _IS_TESTING

# Site URL for building absolute links in emails (no trailing slash)
SITE_URL = env('SITE_URL', default='https://portal.redib.net')

# Wagtail (marketing site CMS)
WAGTAIL_SITE_NAME = 'ReDIB'
WAGTAILADMIN_BASE_URL = SITE_URL

# Redis Configuration
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

# Caching - Use Redis if available, otherwise use dummy cache for local development
USE_REDIS = env.bool('USE_REDIS', default=False)

if USE_REDIS:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    # Dummy cache for local development (no Redis required)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# Security Settings (production)
if not DEBUG:
    # SECURE_SSL_REDIRECT defaults to False because Caddy handles TLS termination.
    # Setting this to True causes an infinite redirect loop behind a reverse proxy.
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)
    CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Sentry Configuration (optional)
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=True
    )

# Debug Toolbar (development only)
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1', 'localhost']

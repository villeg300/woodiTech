"""
Django settings for core project.
"""

import os
from pathlib import Path
from decouple import config
import dj_database_url

# ------------------------------------------
# BASE
# ------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------
# SECURITY
# ------------------------------------------
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

# ------------------------------------------
# APPLICATIONS
# ------------------------------------------
INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party
    'corsheaders',
    'crispy_forms',
    'djmoney',
    
    # Local apps
    'users',
    'store',
    'paiements',
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

# ------------------------------------------
# MIDDLEWARE
# ------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # doit être juste après SecurityMiddleware
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'store.middleware.CartMiddleware',
]

# ------------------------------------------
# URLS & TEMPLATES
# ------------------------------------------
ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'users' / 'templates'],  # templates personnalisés
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ------------------------------------------
# DATABASE
# ------------------------------------------
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL')
    )
}

# ------------------------------------------
# PASSWORD VALIDATION
# ------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ------------------------------------------
# AUTHENTICATION
# ------------------------------------------
AUTH_USER_MODEL = 'users.User'
AUTHENTICATION_BACKENDS = [
    'users.backends.PhoneOrEmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# ------------------------------------------
# INTERNATIONALIZATION
# ------------------------------------------
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'GMT'
USE_I18N = True
USE_TZ = True

# ------------------------------------------
# STATIC FILES
# ------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']  # fichiers static en dev
STATIC_ROOT = BASE_DIR / 'staticfiles'    # fichiers collectés pour prod
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ------------------------------------------
# MEDIA FILES
# ------------------------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ------------------------------------------
# EMAIL (DEV)
# ------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@wooditech.local'

# ------------------------------------------
# PAYMENTS
# ------------------------------------------
STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY', default='')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')

CINETPAY_API_KEY = config('CINETPAY_API_KEY', default='')
CINETPAY_SITE_ID = config('CINETPAY_SITE_ID', default='')
CINETPAY_NOTIFY_URL = config('CINETPAY_NOTIFY_URL', default='')
CINETPAY_RETURN_URL = config('CINETPAY_RETURN_URL', default='')
CINETPAY_CANCEL_URL = config('CINETPAY_CANCEL_URL', default='')

# ------------------------------------------
# DEFAULT PK
# ------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

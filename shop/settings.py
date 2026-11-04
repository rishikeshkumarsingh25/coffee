
"""
Django settings for shop project.
Production-ready configuration for Render + Aiven MySQL.
"""

import os
from pathlib import Path
from decouple import config, Csv

# =====================================
# BASE DIRECTORY
# =====================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =====================================
# DJANGO CORE SETTINGS
# =====================================

SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,testserver',
    cast=Csv()
)

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='',
    cast=Csv()
)


# =====================================
# SECURITY SETTINGS
# =====================================

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = config(
    'SECURE_SSL_REDIRECT',
    default=not DEBUG,
    cast=bool
)

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'


# =====================================
# APPLICATIONS
# =====================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'products',
]

AUTH_USER_MODEL = 'products.User'


# =====================================
# MIDDLEWARE
# =====================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# =====================================
# URL CONFIGURATION
# =====================================

ROOT_URLCONF = 'shop.urls'

WSGI_APPLICATION = 'shop.wsgi.application'


# =====================================
# TEMPLATES
# =====================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'products' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]


# =====================================
# DATABASE CONFIGURATION
# =====================================

DB_ENGINE = config('DB_ENGINE', default='mysql').lower()

if DB_ENGINE == 'sqlite3':

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

elif DB_ENGINE == 'mysql':

    DB_NAME = config('DB_NAME', default='')
    DB_USER = config('DB_USER', default='')
    DB_PASSWORD = config('DB_PASSWORD', default='')
    DB_HOST = config('DB_HOST', default='')
    DB_PORT = config('DB_PORT', default=3306, cast=int)

    if not all([DB_NAME, DB_USER, DB_PASSWORD, DB_HOST]):
        raise ValueError(
            'MySQL environment variables are missing. '
            'Check DB_NAME, DB_USER, DB_PASSWORD and DB_HOST.'
        )

    DB_SSL_CA = config(
        'DB_SSL_CA',
        default=str(BASE_DIR / 'ca.pem')
    )

    DATABASE_OPTIONS = {
        'charset': 'utf8mb4',
    }

    if DB_SSL_CA and Path(DB_SSL_CA).is_file():
        DATABASE_OPTIONS['ssl'] = {
            'ca': DB_SSL_CA,
        }
    else:
        # Enable encrypted MySQL connection when CA file
        # is not available. Add Aiven CA certificate for
        # certificate verification.
        DATABASE_OPTIONS['ssl'] = {}

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
            'OPTIONS': DATABASE_OPTIONS,
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
        }
    }

else:
    raise ValueError(
        'Invalid DB_ENGINE. Use mysql or sqlite3.'
    )


# =====================================
# PASSWORD VALIDATION
# =====================================

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


# =====================================
# LANGUAGE AND TIME
# =====================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'

USE_I18N = True
USE_TZ = True


# =====================================
# STATIC FILES
# =====================================

STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = []

if (BASE_DIR / 'static').exists():
    STATICFILES_DIRS.append(BASE_DIR / 'static')

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}


# =====================================
# MEDIA FILES
# =====================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# =====================================
# EMAIL CONFIGURATION
# =====================================

USE_CONSOLE_EMAIL = config(
    'USE_CONSOLE_EMAIL',
    default=False,
    cast=bool
)

if USE_CONSOLE_EMAIL:
    EMAIL_BACKEND = (
        'django.core.mail.backends.console.EmailBackend'
    )
else:
    EMAIL_BACKEND = (
        'django.core.mail.backends.smtp.EmailBackend'
    )

EMAIL_HOST = config(
    'EMAIL_HOST',
    default='smtp.gmail.com'
)

EMAIL_PORT = config(
    'EMAIL_PORT',
    default=587,
    cast=int
)

EMAIL_USE_TLS = config(
    'EMAIL_USE_TLS',
    default=True,
    cast=bool
)

EMAIL_HOST_USER = config(
    'EMAIL_HOST_USER',
    default=''
)

EMAIL_HOST_PASSWORD = config(
    'EMAIL_HOST_PASSWORD',
    default=''
).replace(' ', '').strip()

DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL',
    default=EMAIL_HOST_USER
)

EMAIL_TIMEOUT = 20


# =====================================
# LOGIN / LOGOUT
# =====================================

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'


# =====================================
# DEFAULT PRIMARY KEY
# =====================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

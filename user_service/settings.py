# user_service/settings.py
import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY    = os.environ.get("SECRET_KEY", "dev-secret-key")
DEBUG         = os.environ.get("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'users.apps.UsersConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'user_service.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'user_service.wsgi.application'

# ──────────────────────────────────────────────────────────────────────────────
# DATABASE
# CORRECTION : CONN_MAX_AGE=60 active le connection pooling Django.
# Sans ça, Django ouvre + ferme une connexion MySQL à CHAQUE requête HTTP.
# Avec 60 : la connexion est réutilisée pendant 60 secondes → beaucoup moins
# de mémoire consommée et de latence réseau.
# ──────────────────────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE':       'django.db.backends.mysql',
        'NAME':         os.environ.get("MYSQL_DATABASE", "user_db"),
        'USER':         os.environ.get("MYSQL_USER", "user_user"),
        'PASSWORD':     os.environ.get("MYSQL_PASSWORD", "ebate124"),
        'HOST': os.environ.get("MYSQL_HOST", "dreamhouse237-db.cbc4i248y7jv.eu-north-1.rds.amazonaws.com"),
        'PORT':         os.environ.get("MYSQL_PORT", "3306"),
        'CONN_MAX_AGE': int(os.environ.get("DB_CONN_MAX_AGE", "60")),  # ← CORRECTION
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'connect_timeout': 10,
        },
    }
}

if 'test' in sys.argv:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

STATIC_URL = 'static/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL  = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ──────────────────────────────────────────────────────────────────────────────
# DRF — pagination globale (filet de sécurité si un ViewSet oublie pagination_class)
# ──────────────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2f")

EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = 'dreamhouse2372025@gmail.com'
EMAIL_HOST_PASSWORD = 'krwq byrr ywtj jwto'

FRONTEND_BASE_URL  = os.environ.get("FRONTEND_BASE_URL", "http://localhost:8000")
TESTING            = "test" in sys.argv
IDENTITY_SERVICE_URL = os.environ.get("IDENTITY_SERVICE_URL", "http://localhost:8001")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{levelname}] {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'users': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}



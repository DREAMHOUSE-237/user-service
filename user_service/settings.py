import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------
# SECRET / DEBUG / ALLOWED HOSTS
# ---------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
DEBUG = os.environ.get("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

# ---------------------------
# Applications
# ---------------------------
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

# ---------------------------
# DATABASE CONFIGURATION
# ---------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get("MYSQL_DATABASE", "user_db"),
        'USER': os.environ.get("MYSQL_USER", "user_user"),
        'PASSWORD': os.environ.get("MYSQL_PASSWORD", "ebate124"),
        'HOST': os.environ.get("MYSQL_HOST", "dreamhouse237-db.cbc4i248y7jv.eu-north-1.rds.amazonaws.com"),
        'PORT': os.environ.get("MYSQL_PORT", "3306"),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# In-memory DB for tests
if 'test' in sys.argv:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}

# ---------------------------
# Password validation
# ---------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------
# Internationalization
# ---------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ---------------------------
# Static & Media
# ---------------------------
STATIC_URL = 'static/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------
# RabbitMQ
# ---------------------------
RABBITMQ_URL = os.environ.get(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost:5672/%2f"
)

# ---------------------------
# Email (Gmail)
# ---------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'dreamhouse2372025@gmail.com'
EMAIL_HOST_PASSWORD = 'krwq byrr ywtj jwto'

# ---------------------------
# Frontend base URL (used in verification emails)
# ---------------------------
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:8000")

# ---------------------------
# Test detection
# ---------------------------
TESTING = "test" in sys.argv

# ---------------------------
# Identity Service
# ---------------------------
IDENTITY_SERVICE_URL = os.environ.get("IDENTITY_SERVICE_URL", "http://localhost:8001")
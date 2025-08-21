"""
Django settings for babaatsite project.
"""

import os
import sys
import types
from pathlib import Path

from babaatsite.secret_utils import load_all_secrets

if "test" in sys.argv:
    # pretend pypdfium2 is a plain Python module
    sys.modules["pypdfium2"] = types.ModuleType("pypdfium2")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# File storage
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

# Secrets management
SECRETS = load_all_secrets()
SUPABASE = SECRETS.get("supabase", {})
S3 = SECRETS.get("s3", {})
REDIS = SECRETS.get("redis", {})
DJANGO_SECRET = SECRETS.get("django_secret", "dev-secret-key")
HOSTS = SECRETS.get("hosts", {})

USE_LOCAL_DB = not SUPABASE
USE_LOCAL_STORAGE = not S3
USE_LOCAL_REDIS = not REDIS

# Storage config
if USE_LOCAL_STORAGE:
    STORAGES = {
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
                "location": MEDIA_ROOT,
            },
        },
    }
else:
    STORAGES = {
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
        "default": {
            "BACKEND": "ocr.storages.MultipartOnlyS3Storage",
            "OPTIONS": {
                "bucket_name": S3.get("bucketname", "media"),
                "access_key": S3.get("accesskey"),
                "secret_key": S3.get("secretkey"),
                "endpoint_url": S3.get("endpoint"),
                "region_name": S3.get("region"),
            },
        },
    }

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

secret = DJANGO_SECRET
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = secret

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

gcp_cloudrun_host = HOSTS.get("GCP_CLOUDRUN_HOST")
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

if gcp_cloudrun_host:
    ALLOWED_HOSTS.append(gcp_cloudrun_host)
else:
    raise ValueError("GCP_CLOUDRUN_HOST environment variable is not set.")


# Application definition

INSTALLED_APPS = [
    "ocr.apps.OcrConfig",  # Include the OCR app
    "django_cleanup.apps.CleanupConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "storages",  # s3 storage supabase
]

MIDDLEWARE = [
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "babaatsite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "babaatsite.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Database config
if USE_LOCAL_DB:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": SUPABASE.get("dbname"),
            "USER": SUPABASE.get("user"),
            "PASSWORD": SUPABASE.get("password"),
            "HOST": SUPABASE.get("host"),
            "PORT": SUPABASE.get("port"),
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa E501
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",  # noqa E501
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",  # noqa E501
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",  # noqa E501
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_FILE_DIRS = [BASE_DIR / "static"]
STATIC_URL = "/static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery settings
# Redis config for Celery
if USE_LOCAL_REDIS:
    CELERY_REDIS_PASSWORD = ""
    CELERY_REDIS_HOST = "localhost"
    CELERY_REDIS_PORT = "6379"
else:
    CELERY_REDIS_PASSWORD = REDIS.get("redis_password", "")
    CELERY_REDIS_HOST = REDIS.get("redis_host", "localhost")
    CELERY_REDIS_PORT = REDIS.get("redis_port", "6379")

CELERY_BROKER_URL = f"redis://:{CELERY_REDIS_PASSWORD}@{CELERY_REDIS_HOST}:{CELERY_REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"redis://:{CELERY_REDIS_PASSWORD}@{CELERY_REDIS_HOST}:{CELERY_REDIS_PORT}/0"
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": 3600,
    "health_check_interval": 25,
    "socket_timeout": 10,
    "socket_connect_timeout": 10,
    "socket_keepalive": True,
}
CELERY_BROKER_POOL_LIMIT = 2
CELERY_BROKER_MAX_CONNECTIONS = 4
CELERY_BROKER_HEARTBEAT = 30
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_TIME_LIMIT = 10 * 60  # 10 minutes -> 40 pages (conservative est.)
CELERY_RESULT_EXPIRES = 10 * 60  # 10 minutes -> 40 pages (conservative est.)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
    "retry_on_timeout": True,
    "health_check_interval": 25,
    "socket_keepalive": True,
}

CELERY_TASK_PUBLISH_RETRY = True
CELERY_TASK_PUBLISH_RETRY_POLICY = {
    "max_retries": 5,
    "interval_start": 0,
    "interval_step": 0.5,
    "interval_max": 5,
}

SECRET_KEY = DJANGO_SECRET
DEBUG = True

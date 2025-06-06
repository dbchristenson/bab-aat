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
DJANGO_SECRET = SECRETS.get("django_secret", "")
HOSTS = SECRETS.get("hosts", {})

# validate that all secrets contain some value
for secret in [SUPABASE, S3, REDIS, DJANGO_SECRET, HOSTS]:
    if not secret:
        raise ValueError(
            f"One or more secrets are missing or empty. {secret} broke first."
        )

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
CELERY_BROKER_URL = REDIS.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": 3600,
    "health_check_interval": 25,
    "socket_timeout": 10,
    "socket_connect_timeout": 10,
}
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_RESULT_BACKEND = REDIS.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
)
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_RESULT_EXPIRES = 30 * 60  # 30 minutes

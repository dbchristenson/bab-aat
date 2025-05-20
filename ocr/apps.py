from django.apps import AppConfig


class OcrConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ocr"

    def ready(self):
        from .config import configure_logging

        # You can customize the log level here, e.g., from settings
        # from django.conf import settings
        # log_level = getattr(settings, 'OCR_APP_LOG_LEVEL', 'INFO')
        # configure_logging(log_level)
        configure_logging()  # Uses INFO or level set in configure_logging

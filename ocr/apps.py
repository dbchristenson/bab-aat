from django.apps import AppConfig


class OcrConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ocr"

    def ready(self):
        from .config import configure_logging

        configure_logging()  # Uses INFO or level set in configure_logging

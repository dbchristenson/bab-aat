from pathlib import Path

from django.conf import settings
from loguru import logger


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure logging settings for the application.

    This function sets up the Loguru logger with the specified log path,
    rotation, compression, and retention settings.

    Args:
        log_level (str): The logging level to set for the logger.
                         Defaults to "INFO".

    Returns:
        None
    """
    # Default to ./logs if LOG_PATH is not set in Django settings
    log_path_setting = getattr(settings, "LOG_PATH", "./logs")

    # Ensure log_path is a Path object
    if isinstance(log_path_setting, str):
        log_path = Path(log_path_setting)
    else:
        log_path = log_path_setting

    svc_log_name = getattr(settings, "SVC_LOG_NAME", "ocr_app.log")
    svc_rotation = getattr(settings, "SVC_ROTATION", "10 MB")
    svc_compression = getattr(settings, "SVC_COMPRESSION", "zip")
    svc_retention = getattr(settings, "SVC_RETENTION", "10 days")

    # Ensure the log directory exists
    log_path.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_path / svc_log_name,
        rotation=svc_rotation,
        compression=svc_compression,
        retention=svc_retention,
        level=log_level.upper(),
        format="{time} {level} {message}",
        enqueue=True,  # For asynchronous logging
        backtrace=True,  # Better tracebacks for errors
        diagnose=True,  # More detailed error messages
    )

    logger.info(
        f"Loguru logging configured. Level: {log_level.upper()}. "
        f"Log file: {log_path / svc_log_name}"
    )


def configure_modal() -> None:
    pass

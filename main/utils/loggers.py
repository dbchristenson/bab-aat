import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
    """Robust logging setup that survives PaddleOCR's configuration"""
    # Create logs directory if needed
    os.makedirs("main/logs", exist_ok=True)

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear ALL existing handlers and filters
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    for filter in logger.filters[:]:
        logger.removeFilter(filter)

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # File handler with rotation
    file_handler = RotatingFileHandler(
        "main/logs/detect_objs.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Prevent propagation to parent loggers
    logger.propagate = False

    # Immediately test
    logger.info("Logging system initialized successfully")
    file_handler.flush()
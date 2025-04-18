import argparse
import datetime as dt
import logging
import os
from typing import Optional

from paddleocr import PaddleOCR

from ocr.main.utils.configs import load_config, with_config
from ocr.main.utils.extract_ocr_results import get_bbox  # noqa: E501
from ocr.main.utils.extract_ocr_results import get_confidence, get_ocr
from ocr.main.utils.loggers import setup_logging
from ocr.models import Detection, Page


@with_config
def config_ocr(config=None):
    """
    Configure the OCR network.

    Args:
        config (dict): Configuration dictionary for the OCR network.
    """
    logging.info("Configuring OCR network...")

    paddle_conf = config.get("paddle")

    try:
        ocr = PaddleOCR(**paddle_conf)
    except Exception as e:
        logging.exception("Failed to configure OCR network.")
        raise e

    logging.info("OCR network configured.")

    return ocr

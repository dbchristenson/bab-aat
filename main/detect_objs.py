import argparse
import datetime as dt
import logging
from collections import Counter

from models import Detection, Document, Page
from paddleocr import PaddleOCR
from peewee import *
from utils.configs import with_config
from utils.db_routing import connect_to_db


@with_config
def config_ocr(config=None):
    """
    Configure the OCR network.

    Args:
        config (dict): Configuration dictionary for the OCR network.
    """
    logging.info("Configuring OCR network...")

    try:
        ocr = PaddleOCR(**config)
    except Exception as e:
        logging.exception("Failed to configure OCR network.")
        raise e

    logging.info("OCR network configured.")

    return ocr


def get_pages_to_process():
    """
    Get all pages that have not been processed yet.
    """

    pages = (
        Page.select()
        .join(Detection, JOIN.LEFT_OUTER)
        .where(Detection.id.is_null())
    )

    logging.info(f"Retrieved {len(pages)} pages to process.")

    return pages

@with_config
def apply_network(ocr: PaddleOCR, db_args):
    """
    Apply the network to images in the given directory. The images
    are converted from PDF to PNG page by page.

    Args:
        ocr (PaddleOCR): The OCR network to apply.
        db_args (dict): Database connection arguments.
    """
    logging.info("Applying OCR network to images...")

    connect_to_db(**db_args)

    # Get all page images
    pages = get_pages_to_process()

    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--detection_config", type=str, default="configs/paddle_on_local_db.json")
    args = parser.parse_args()

    paddle_args = args.paddle
    db_args = args.db

    ocr = config_ocr(paddle_args)

    apply_network("olombendo_output")

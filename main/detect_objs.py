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


def apply_network(ocr: PaddleOCR):
    """
    Apply the network to images in the given directory. The images
    are converted from PDF to PNG page by page.
    """

    # Get all page images
    pages = get_pages_to_process()

    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--paddle_config", type=str, default="configs/paddle_config.json")
    args = parser.parse_args()

    ocr = config_ocr(args.paddle_config)

    apply_network("olombendo_output")

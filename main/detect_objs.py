import argparse
import datetime as dt
import logging
import os

from models import Detection, Page
from paddleocr import PaddleOCR
from peewee import *
from utils.configs import with_config
from utils.db_routing import connect_to_db
from utils.extract_ocr_results import (crop_image, get_bbox, get_confidence,
                                       get_ocr)
from utils.loggers import setup_logging


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


def get_pages_to_process(rerun: bool = False, rerun_page_ids: list[int] = False):
    """
    Get all pages that have not been processed yet.
    """
    if rerun:
        query = Page.select()
        if rerun_page_ids is not None:
            query = query.where(Page.id.in_(rerun_page_ids))

        deleted_count = (
            Detection.delete().
            where(Detection.page_id.in_(query))
            .execute()
        )
        logging.info(f"Deleted {deleted_count} detections.")

    pages = (
        Page.select()
        .join(Detection, JOIN.LEFT_OUTER)
        .where(Detection.id.is_null())
    )

    logging.info(f"Retrieved {len(pages)} pages to process.")
    return pages


def get_detections(ocr: PaddleOCR, page: Page, output_dir: str = "cropped_images"):
    """
    Get all detections for a given page.

    Args:
        page (Page): The page object to get detections for.
    """

    result = ocr.ocr(page.path, cls=True)

    for line in result[0]:
        bbox = get_bbox(line)
        ocr_text = get_ocr(line)
        confidence = get_confidence(line)

        logging.info(f"Detected text: '{ocr_text}' with confidence: {confidence} at {bbox}")

        # Bbox -> [[i0], [i1], [i2], [i3]]
        # Drawn bottom left -> bottom right -> top right -> top left
        x_center = (bbox[0][0] + bbox[2][0]) / 2
        y_center = (bbox[0][1] + bbox[2][1]) / 2

        width = bbox[2][0] - bbox[0][0]
        height = bbox[2][1] - bbox[0][1]

        img = crop_image(page.path, bbox)
        save_path = os.path.join(output_dir, f"{page.id}.png")
        img.save(save_path)

        Detection.create(
            page=page,
            ocr_text=ocr_text,
            x_center=x_center,
            y_center=y_center,
            width=width,
            height=height,
            confidence=confidence,
            cropped_img_path=save_path,
            created_at=dt.datetime.now(),
        )

        logging.info(f"Created detection for page {page.id} with text: '{ocr_text}'")

    return


@with_config
def apply_network(ocr: PaddleOCR, config=None, output_dir=None):
    """
    Apply the network to images in the given directory. The images
    are converted from PDF to PNG page by page.

    Args:
        ocr (PaddleOCR): The OCR network to apply.
        db_args (dict): Database connection arguments.
    """
    logging.info("Applying OCR network to images...")

    db_conf = config.get("db")
    db = connect_to_db(**db_conf)

    # Get all page images
    with db.atomic():
        pages = get_pages_to_process(output_dir)

    # Apply detections and save results
    for page in pages:
        logging.info(f"Processing page {page.id}...")
        try:
            get_detections(ocr, page)
        except Exception as e:
            logging.error(f"Failed to process page {page.id}: {e}")
            continue

    logging.info("Finished processing all pages.")

    return


if __name__ == "__main__":
    setup_logging()
    logging.info("Starting OCR application...")

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="main/configs/detect_objs/paddle_on_local_db.json")
    args = parser.parse_args()

    config = args.config

    output_dir = config.get("output_dir", "cropped_images")
    os.makedirs(output_dir, exist_ok=True)
    logging.info(f"Output directory created at {output_dir}.")

    ocr = config_ocr(config=config)

    apply_network(ocr=ocr, config=config, output_dir=output_dir)



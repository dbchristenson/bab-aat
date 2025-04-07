import argparse
import datetime as dt
import logging
import os
from typing import Optional

from models import Detection, Page
from paddleocr import PaddleOCR
from peewee import JOIN
from utils.configs import load_config, with_config
from utils.db_routing import connect_to_db
from utils.extract_ocr_results import (
    crop_image,
    get_bbox,
    get_confidence,
    get_ocr,
)
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


def handle_detection_deletion(
    page_ids: Optional[list[int]] = None,
) -> tuple[int, int]:
    """
    Delete detection records and their associated cropped image files.

    Args:
        page_ids: List of page IDs whose detections should be deleted,
                  if None, all detections will be deleted.

    Returns:
        tuple: (deleted_records_count, deleted_files_count)
    """
    # Query for detections to delete
    detections_query = Detection.select(Detection.cropped_img_path)
    if page_ids is not None:
        detections_query = detections_query.where(Detection.page.in_(page_ids))

    # Delete associated image files
    deleted_files = 0
    for detection in detections_query:
        if detection.cropped_img_path and os.path.exists(
            detection.cropped_img_path
        ):
            try:
                os.remove(detection.cropped_img_path)
                deleted_files += 1
            except OSError as e:
                logging.warning(
                    f"Failed to delete {detection.cropped_img_path}: {e}"
                )

    # Delete database records
    delete_query = Detection.delete()
    if page_ids is not None:
        delete_query = delete_query.where(Detection.page.in_(page_ids))

    deleted_records = delete_query.execute()

    logging.info(
        f"Deleted {deleted_records} detection records "
        f"and {deleted_files} image files"
    )
    return deleted_records, deleted_files


def get_pages_to_process(
    rerun: bool = False, rerun_page_ids: Optional[list[int]] = None
):
    """
    Get all pages that have not been processed yet.

    Args:
        rerun (bool): Whether to rerun the detections.
        rerun_page_ids (list): List of page IDs to rerun.
    """
    if rerun:
        if rerun_page_ids is not None and not isinstance(rerun_page_ids, list):
            raise ValueError(
                "rerun_page_ids must be a list of integers or None"
            )

        # Handle deletion
        handle_detection_deletion(rerun_page_ids)

    pages = (
        Page.select()
        .join(Detection, JOIN.LEFT_OUTER)
        .where(Detection.id.is_null())
    )

    logging.info(f"Retrieved {len(pages)} pages to process.")
    return pages


def get_detections(
    ocr: PaddleOCR, page: Page, output_dir: str = "cropped_images"
):
    """
    Get all detections for a given page.

    Args:
        page (Page): The page object to get detections for.
    """

    document = page.document
    result = ocr.ocr(page.img_path, cls=True)
    logging.info(f"Detected {len(result[0])} text lines on page {page.id}.")

    for idx, line in enumerate(result[0]):
        bbox = get_bbox(line)
        ocr_text = get_ocr(line)
        confidence = get_confidence(line)

        logging.info(
            f"Detected: '{ocr_text}' with confidence: {confidence} at {bbox}"
        )

        # Bbox -> [[i0], [i1], [i2], [i3]]
        # Drawn bottom left -> bottom right -> top right -> top left
        x_center = (bbox[0][0] + bbox[2][0]) / 2
        y_center = (bbox[0][1] + bbox[2][1]) / 2

        width = bbox[2][0] - bbox[0][0]
        height = bbox[2][1] - bbox[0][1]

        img = crop_image(page.img_path, bbox)
        save_path = os.path.join(output_dir, f"{page.id}_detection_{idx}.png")
        img.save(save_path)

        Detection.create(
            document=document,
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

        logging.info(
            f"Created detection for page {page.id} with text: '{ocr_text}'"
        )

    return


@with_config
def apply_network(ocr: PaddleOCR, config=None):
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

    detections_conf = config.get("detections")
    output_dir = detections_conf.get("output_dir")
    rerun = detections_conf.get("rerun", False)
    rerun_page_ids = detections_conf.get("rerun_page_ids", None)

    # Get all page images
    with db.atomic():
        params = {"rerun": rerun, "rerun_page_ids": rerun_page_ids}
        pages = get_pages_to_process(**params)

    # Apply detections and save results
    for page in pages:
        logging.info(f"Processing page {page.id}...")
        try:
            get_detections(ocr, page, output_dir=output_dir)
        except Exception as e:
            logging.error(f"Failed to process page {page.id}: {e}")
            continue

    logging.info("Finished processing all pages.")

    return


if __name__ == "__main__":
    setup_logging()
    logging.info("Starting OCR application...")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=str,
        default="main/configs/detect_objs/paddle_on_local_db.json",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    output_dir = config.get("output_dir", "cropped_images")
    os.makedirs(output_dir, exist_ok=True)
    logging.info(f"Output directory created at {output_dir}.")

    ocr = config_ocr(config=args.config)

    apply_network(ocr=ocr, config=args.config)

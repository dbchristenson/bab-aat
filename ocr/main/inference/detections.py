import logging

from paddleocr import PaddleOCR

from ocr.main.utils.configs import with_config
from ocr.main.utils.extract_ocr_results import get_bbox  # noqa: E501
from ocr.main.utils.extract_ocr_results import get_confidence, get_ocr
from ocr.main.utils.loggers import setup_logging
from ocr.models import Detection, Document, Page

setup_logging(logger_name="detections")


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


def get_page_detections(
    page: Page, ocr: PaddleOCR, param_config: str
) -> list[Detection]:
    """
    Get detections for a given page using the OCR network.

    Args:
        page (Page): The page object containing the image and metadata.
        ocr (PaddleOCR): The configured OCR network.

    Returns:
        list[Detection]: List of detection objects for the page.
    """
    # Perform OCR on the page image
    ocr_results = ocr.ocr(page.image.path, cls=True, bin=True)
    lines = ocr_results[0]

    logging.info(
        f"[{param_config}] Detected {len(lines)} lines on page {page.id}"
    )

    # Extract bounding boxes, confidence scores, and text from OCR results
    detections: list[Detection] = []
    for line in lines:
        bbox = get_bbox(line)
        confidence = get_confidence(line)
        text = get_ocr(line)

        logging.debug(
            f"[{param_config}] Detected text: {text}, bbox: {bbox}, confidence: {confidence}"  # noqa: E501
        )

        det = Detection(
            page_id=page.id,
            bbox=bbox,
            confidence=confidence,
            text=text,
            param_config=param_config,
        )

        det.save()  # Save the detection to the database

        detections.append(det)

    logging.info(f"[{param_config}] Saved detection for page {page.id}")

    return detections


def analyze_document(
    document_id: int, ocr: PaddleOCR, param_config: str
) -> list[Detection]:
    """
    Analyze a document by processing each page and extracting detections.
    The returned detections are stored in the database, so you may throw
    them away if you don't need them.

    Args:
        document_id (int): The ID of the document to analyze.
        ocr (PaddleOCR): The configured OCR network.
        param_config (str): The name of the param_config or model used.

    Returns:
        list[Detection]: List of detection objects for the document.
    """

    document = Document.objects.get(id=document_id)
    pages = Page.objects.filter(document=document)

    all_detections = []

    for page in pages:
        detections = get_page_detections(page, ocr, param_config)
        all_detections.extend(detections)

    return all_detections

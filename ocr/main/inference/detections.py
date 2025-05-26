import cv2 as cv
import numpy as np
from loguru import logger
from paddleocr import PaddleOCR
from pypdfium2 import PdfDocument

from ocr.main.inference.preprocessing.boundaries import figure_table_extraction
from ocr.main.utils.extract_ocr_results import (
    get_bbox,
    get_confidence,
    get_ocr,
)
from ocr.main.utils.page_to_img import rotate_landscape
from ocr.models import Detection, Document, Page


def _extract_detections_from_image(
    image_np: np.ndarray,
    ocr: PaddleOCR,
    config_id: int,
    page_db_id: int,
    min_confidence: float = 0.6,
) -> list[Detection]:
    """
    Get detections for a given image numpy array using the OCR network.
    Detections are not saved to the database by this function.

    Args:
        image_np (np.ndarray): The image numpy array to process.
        ocr (PaddleOCR): The configured OCR network.
        config_id (int): The id of the OCRConfig object used.
        page_db_id (int): The ID of the Page object this image belongs to.
        min_confidence (float): Minimum confidence threshold for detections.

    Returns:
        list[Detection]: List of detection objects for the image.
    """
    # Perform OCR on the image
    ocr_results = ocr.ocr(image_np, cls=True, bin=True)
    if (
        not ocr_results or not ocr_results[0]
    ):  # Ensure results are not None or empty
        logger.info(
            f"[{config_id}] No OCR results for image w/ page id = {page_db_id}"  # noqa E501
        )
        return []

    lines = ocr_results[0]

    logger.info(
        f"[{config_id}] Detected {len(lines)} lines on image for page ID {page_db_id}"  # noqa E501
    )

    detections: list[Detection] = []
    for line_idx, line_data in enumerate(lines):
        bbox = get_bbox(line_data)
        confidence = get_confidence(line_data)
        text = get_ocr(line_data)

        if confidence < min_confidence:
            logger.debug(
                f"[{config_id}] Line {line_idx} on page ID {page_db_id} "
                f"has low confidence ({confidence}). Skipping."
            )
            continue

        logger.debug(
            f"[{config_id}] Page ID {page_db_id} - Line {line_idx}: Text: {text}, BBox: {bbox}, Confidence: {confidence}"  # noqa E501
        )

        det = Detection(
            page_id=page_db_id,  # Use the passed page_db_id
            bbox=bbox,
            confidence=confidence,
            text=text,
            config_id=config_id,
        )
        detections.append(det)

    logger.info(
        f"[{config_id}] Extracted {len(detections)} detections for page ID {page_db_id}"  # noqa E501
    )

    return detections


def _save_adjusted_detections(
    detections: list[Detection], offset_x: int, offset_y: int
) -> list[Detection]:
    """
    Adjusts the bbox coordinates of detections by an offset and saves them.

    Args:
        detections (list[Detection]): List of raw detection objects.
        offset_x (int): The x-coordinate offset to add to bbox points.
        offset_y (int): The y-coordinate offset to add to bbox points.

    Returns:
        list[Detection]: List of saved detection objects with adjusted bboxes.
    """
    saved_detections = []
    for det in detections:
        # Adjust bbox: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        adjusted_bbox = [[p[0] + offset_x, p[1] + offset_y] for p in det.bbox]
        det.bbox = adjusted_bbox
        det.save()
        saved_detections.append(det)
        logger.debug(
            f"[{det.config.name}] Saved detection ID {det.id} for page ID {det.page_id} with adjusted bbox: {det.bbox}"  # noqa E501
        )
    return saved_detections


def _get_pdf_object(document_id: int) -> PdfDocument:
    """
    Get the PDF document object for a given document ID.

    Args:
        document_id (int): The ID of the document.

    Returns:
        PdfDocument: The PDF document object.
    """
    logger.info(f"Fetching document with ID: {document_id} for PDF object")
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(
            f"Document with ID {document_id} not found in _get_pdf_object."
        )
        raise

    try:
        with document.file.open("rb") as f:  # Open in binary read mode
            pdf_bytes = f.read()
        logger.info(f"Read {len(pdf_bytes)} bytes from document {document_id}")
        pdf = PdfDocument(pdf_bytes)  # Load from bytes
        logger.info(f"Successfully loaded PDF for document {document_id}")
        return pdf
    except Exception as e:
        logger.error(
            f"Error opening or loading PDF for document {document_id}: {e}",
            exc_info=True,
        )
        raise


def _page_to_image(page_obj, page_render_scale: float = 4.0):
    """
    Convert a PDF page object to an image.

    Args:
        page_obj: The PDF page object.
        page_render_scale (float): Scale factor for rendering the page.

    Returns:
        PIL.Image: The rendered image of the page.
    """
    # Render the page to an image
    page_obj = rotate_landscape(page_obj)
    page_bitmap = page_obj.render(scale=page_render_scale)
    page_pil = page_bitmap.to_pil()
    image_np = np.array(page_pil)

    if len(image_np.shape) == 3:
        if image_np.shape[2] == 3:  # RGB
            gray_image_np = cv.cvtColor(image_np, cv.COLOR_RGB2GRAY)
        elif image_np.shape[2] == 4:  # RGBA
            gray_image_np = cv.cvtColor(image_np, cv.COLOR_RGBA2GRAY)
        else:  # Should not happen with typical PIL images from PDF
            gray_image_np = image_np  # Fallback, but unlikely
    else:  # Already grayscale or single channel
        gray_image_np = image_np

    return gray_image_np


def _create_page_in_db(document_id: int, page_number: int) -> Page:
    """
    Create a Page object in the database for a given doc ID and page number.
    If the Page object already exists, it will not be created again.

    Args:
        document_id (int): The ID of the document.
        page_number (int): The page number (0-indexed).

    Returns:
        Page: The Page object created or retrieved from the database.
    """
    page_db, created = Page.objects.get_or_create(
        document_id=document_id, page_number=page_number
    )

    if created:
        logger.info(
            f"Created Page object for doc {document_id}, page {page_number}"
        )

    return page_db


def analyze_document(
    document_id: int,
    ocr: PaddleOCR,
    config_id: int,
    figure_kwargs: dict = None,
    table_kwargs: dict = None,
) -> list[Detection]:
    """
    Analyze a document by processing each page, extracting figure and table
    regions, performing OCR on these regions, and saving adjusted detections.

    Args:
        document_id (int): The ID of the document to analyze.
        ocr (PaddleOCR): The configured OCR network.
        param_config (str): The name of the param_config or model used.
        figure_kwargs (dict, optional): Arguments for figure extraction.
        table_kwargs (dict, optional): Arguments for table extraction.

    Returns:
        list[Detection]: List of all saved detection objects for the document.
    """
    logger.info(
        f"Analyze document called for doc: {document_id}, config: {config_id}"
    )

    if figure_kwargs is None:
        figure_kwargs = {}
    if table_kwargs is None:
        table_kwargs = {}

    pdf = _get_pdf_object(document_id)
    logger.info(
        f"Loaded PDF document with {len(pdf)} pages for document {document_id}"
    )  # noqa E501
    all_document_detections: list[Detection] = []

    from ocr.models import OCRConfig  # Local import

    try:
        ocr_config_model_instance = OCRConfig.objects.get(pk=config_id)
        param_config_name = ocr_config_model_instance.name
    except OCRConfig.DoesNotExist:
        logger.warning(
            f"OCRConfig with ID {config_id} not found. Using ID as name."
        )
        param_config_name = str(config_id)

    try:
        page_render_scale = ocr_config_model_instance.config["scale"]
    except KeyError:
        logger.warning(
            f"Scale not found in OCRConfig with ID {config_id}. Using default."
        )
        page_render_scale = 4.0

    # Iterate through each page of the PDF
    for page_idx, page_obj in enumerate(pdf):
        page_number = page_idx + 1
        logger.info(
            f"[{config_id}] Processing page {page_number} for document {document_id}"  # noqa E501
        )

        page_im = _page_to_image(page_obj, page_render_scale)

        # Create page in db
        try:
            page_db = _create_page_in_db(document_id, page_number)
        except Exception as e:
            logger.error(
                f"Error creating page in DB for doc {document_id}, page {page_number}: {e}",  # noqa E501
                exc_info=True,
            )
            continue

        figure_im, table_im, figure_offset, table_offset = (
            figure_table_extraction(
                page_im, figure_kwargs=figure_kwargs, table_kwargs=table_kwargs
            )
        )

        figure_dets = _extract_detections_from_image(
            figure_im,
            ocr,
            config_id,
            page_db.id,
        )
        table_dets = _extract_detections_from_image(
            table_im,
            ocr,
            config_id,
            page_db.id,
        )

        saved_figure_dets = _save_adjusted_detections(
            figure_dets, figure_offset[0], figure_offset[1]
        )
        saved_table_dets = _save_adjusted_detections(
            table_dets, table_offset[0], table_offset[1]
        )

        all_document_detections.extend(saved_figure_dets)
        all_document_detections.extend(saved_table_dets)

        page_obj.close()

    pdf.close()
    logger.info(
        f"[{param_config_name}] Completed document {document_id}. "
        f"Total detections: {len(all_document_detections)}"
    )

    return all_document_detections

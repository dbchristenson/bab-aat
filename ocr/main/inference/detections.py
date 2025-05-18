import logging

import numpy as np
from paddleocr import PaddleOCR
from pypdfium2 import PdfDocument

from ocr.main.inference.preprocessing.boundaries import figure_table_extraction
from ocr.main.utils.extract_ocr_results import (
    get_bbox,
    get_confidence,
    get_ocr,
)
from ocr.main.utils.loggers import setup_logging
from ocr.main.utils.page_to_img import rotate_landscape
from ocr.models import Detection, Document

setup_logging(logger_name="detections")


def _extract_detections_from_image(
    image_np: np.ndarray, ocr: PaddleOCR, param_config: str, page_db_id: int
) -> list[Detection]:
    """
    Get detections for a given image numpy array using the OCR network.
    Detections are not saved to the database by this function.

    Args:
        image_np (np.ndarray): The image numpy array to process.
        ocr (PaddleOCR): The configured OCR network.
        param_config (str): The name of the param_config or model used.
        page_db_id (int): The ID of the Page object this image belongs to.

    Returns:
        list[Detection]: List of detection objects for the image.
    """
    # Perform OCR on the image
    ocr_results = ocr.ocr(image_np, cls=True, bin=True)
    if (
        not ocr_results or not ocr_results[0]
    ):  # Ensure results are not None or empty
        logging.info(
            f"[{param_config}] No OCR results for image w/ page id = {page_db_id}"  # noqa E501
        )
        return []

    lines = ocr_results[0]

    logging.info(
        f"[{param_config}] Detected {len(lines)} lines on image for page ID {page_db_id}"  # noqa E501
    )

    detections: list[Detection] = []
    for line_idx, line_data in enumerate(lines):
        bbox = get_bbox(line_data)
        confidence = get_confidence(line_data)
        text = get_ocr(line_data)

        logging.debug(
            f"[{param_config}] Page ID {page_db_id} - Line {line_idx}: Text: {text}, BBox: {bbox}, Confidence: {confidence}"  # noqa E501
        )

        det = Detection(
            page_id=page_db_id,  # Use the passed page_db_id
            bbox=bbox,
            confidence=confidence,
            text=text,
            param_config=param_config,
        )
        detections.append(det)

    logging.info(
        f"[{param_config}] Extracted {len(detections)} detections for page ID {page_db_id}"  # noqa E501
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
        logging.debug(
            f"[{det.param_config}] Saved detection ID {det.id} for page ID {det.page_id} with adjusted bbox: {det.bbox}"  # noqa E501
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
    document = Document.objects.get(id=document_id)
    document_file_path = document.file.path
    pdf = PdfDocument(document_file_path)

    return pdf


def analyze_document(
    document_id: int,
    ocr: PaddleOCR,
    config_id: int,
    page_render_scale: float = 4.0,
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
        page_render_scale (float): Scale factor for rendering pages to images.
        figure_kwargs (dict, optional): Arguments for figure extraction.
        table_kwargs (dict, optional): Arguments for table extraction.

    Returns:
        list[Detection]: List of all saved detection objects for the document.
    """
    logging.info("Analyze document function called")
    print("analyze_document function called")
    if figure_kwargs is None:
        figure_kwargs = {}
    if table_kwargs is None:
        table_kwargs = {}

    pdf = _get_pdf_object(document_id)
    all_document_detections: list[Detection] = []
    logging.info("converted pdf to pdfium object")

    for page_idx, page_obj in enumerate(pdf):
        page_number = page_idx + 1
        logging.info(
            f"[{config_id}] Processing page {page_number} for document {document_id}"  # noqa E501
        )

        page_obj = rotate_landscape(page_obj)
        page_bitmap = page_obj.render(scale=page_render_scale)
        page_im = page_bitmap.to_pil()

        extraction_kwargs = {**figure_kwargs, **table_kwargs}
        figure_im, table_im = figure_table_extraction(
            page_im, extraction_kwargs
        )

        logging.info(f"figure_im returned? {bool(figure_im)}")
        logging.info(f"table_im returned? {bool(table_im)}")

    return all_document_detections

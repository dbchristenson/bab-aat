import pymupdf

from ocr.main.inference.postprocessing.pipeline_steps import _rescale_bbox
from ocr.main.utils.page_to_img import rotate_landscape
from ocr.main.utils.pdf_utils import get_pdf_object
from ocr.models import Detection


def _load_pdf_and_rotate(document_id: int) -> list[pymupdf.Page]:
    """
    Load the PDF document and rotate it to landscape orientation.

    Args:
        document_id (int): The ID of the document.

    Returns:
        list[pymupdf.Page]: The loaded and rotated PDF document.
    """
    pdf = get_pdf_object(document_id, pdf_lib="pymupdf")

    rotated_pages = []

    # Rotate all pages to landscape
    for page in pdf:
        rotated_page = rotate_landscape(page)
        rotated_pages.append(rotated_page)

    return rotated_pages


def _draw_bboxes_on_page(page: pymupdf.Page, page_no: int, model: str):
    """
    Draw bounding boxes for detections/tags depending on which model
    is passed to the function.

    This function does not draw text on the page. It only draws
    bounding boxes.

    Args:
        page (pdfium.PdfPage): The PDF page to draw on.
        page_no (int): The page number to draw on. 1-indexed.
        model (str): The model to use for drawing. Can be either
                     "detection" or "tag".
    """
    from ocr.models import Detection, Tag

    if model == "detection":
        detections = Detection.objects.filter(page__page_number=page_no)
        for detection in detections:
            bbox = _rescale_bbox(
                detection.bbox, detection.config.config["scale"]
            )
    elif model == "tag":
        tags = Tag.objects.filter(page__page_number=page_no)
        for tag in tags:
            pass
            # tag bboxs are already unscaled
    return


def visualize_document_results(document_id: int, model: str) -> None:
    """
    Visualize the results of the OCR detection on the document.

    The results may be either detections or tags, depending on the model
    used. The function will draw the bounding boxes on the document
    and return the imaged document with the drawn bounding boxes.

    This function will not overwrite the original document nor will it
    save the document to the database. It is intended for visualization
    and to be rendered in a web application upon request.

    Args:
        document_id (int): The ID of the document to visualize.
        model (str): The model to use for visualization. Can be either
                     "detection" or "tag".

    Returns:
        images
    """
    # Load the document and rotate the pages
    document_pages = _load_pdf_and_rotate(document_id)
    annotated_pages = []

    # Draw bounding boxes on each page
    for idx, page in enumerate(document_pages):
        page_no = idx + 1
        _draw_bboxes_on_page(page, page_no, model)

    return

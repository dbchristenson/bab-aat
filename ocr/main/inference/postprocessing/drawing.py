from pathlib import Path

import pymupdf
from django.conf import settings

from ocr.main.utils.page_to_img import rotate_landscape
from ocr.main.utils.pdf_utils import get_pdf_object
from ocr.models import Detection, Page


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
        rotated_page = rotate_landscape(page, pdf_lib="pymupdf")
        rotated_pages.append(rotated_page)

    return rotated_pages


def _draw_bboxes_on_page(
    page: pymupdf.Page,
    page_obj: Page,
    config_id: int,
    render_scale: float = 2.0,
):
    """
    Draw bounding boxes for detections on a specific page.

    Args:
        page (pymupdf.Page): The PyMuPDF page to draw on.
        page_obj (Page): Django Page model instance.
        config_id (int): The OCR config ID to filter detections.
        render_scale (float): Scale factor used for rendering the page.
    """
    from ocr.models import OCRConfig

    # Get detections for this page and config
    detections = Detection.objects.filter(page=page_obj, config_id=config_id)

    # Get the original OCR scale from config
    config = OCRConfig.objects.get(id=config_id)
    ocr_scale = config.config.get("scale", 4.0)

    for detection in detections:
        # Bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        bbox_points = detection.bbox

        # Convert to rectangle coordinates and scale appropriately
        # The bbox was saved at ocr_scale, but we're rendering at render_scale
        scale_factor = render_scale / ocr_scale

        x_coords = [point[0] * scale_factor for point in bbox_points]
        y_coords = [point[1] * scale_factor for point in bbox_points]

        x1, x2 = min(x_coords), max(x_coords)
        y1, y2 = min(y_coords), max(y_coords)

        # Create rectangle from bbox coordinates
        rect = pymupdf.Rect(x1, y1, x2, y2)

        # Draw rectangle (red border, no fill)
        page.draw_rect(rect, color=(1, 0, 0), width=2)

        # Optional: Add text label
        if detection.text and len(detection.text.strip()) > 0:
            # Position text slightly above the bbox
            text_point = pymupdf.Point(x1, y1 - 5)
            page.insert_text(
                text_point, detection.text[:20], fontsize=8, color=(1, 0, 0)
            )


def visualize_document_results(document_id: int, config_id: int) -> list[str]:
    """
    Create annotated images for all pages of a document with OCR results.

    Args:
        document_id (int): The document ID.
        config_id (int): The OCR config ID.

    Returns:
        list[str]: List of file paths to the generated images.
    """
    # Use a consistent render scale - we'll use 2x for good quality
    render_scale = 2.0

    # Load PDF and get pages
    pdf_pages = _load_pdf_and_rotate(document_id)
    django_pages = Page.objects.filter(document_id=document_id).order_by(
        "page_number"
    )

    # Create output directory
    output_dir = (
        Path(settings.MEDIA_ROOT)
        / "ocr_results"
        / str(document_id)
        / str(config_id)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []

    for pdf_page, django_page in zip(pdf_pages, django_pages):
        # Draw bounding boxes on the page
        _draw_bboxes_on_page(pdf_page, django_page, config_id, render_scale)

        # Convert page to image with the same scale used for drawing
        pix = pdf_page.get_pixmap(
            matrix=pymupdf.Matrix(render_scale, render_scale)
        )

        # Save as PNG
        output_filename = f"page_{django_page.page_number}_annotated.png"
        output_path = output_dir / output_filename
        pix.save(str(output_path))

        # Store relative path for URL generation
        relative_path = (
            f"ocr_results/{document_id}/" f"{config_id}/{output_filename}"
        )
        generated_files.append(relative_path)

    return generated_files

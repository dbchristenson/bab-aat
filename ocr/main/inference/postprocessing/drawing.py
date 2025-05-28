from pathlib import Path

import pymupdf
from django.conf import settings
from loguru import logger

from ocr.main.utils.pdf_utils import get_pdf_object
from ocr.models import Detection, Page


def _load_pdf_and_rotate(document_id: int) -> list[pymupdf.Page]:
    """
    Load the PDF document WITHOUT rotating it.

    Args:
        document_id (int): The ID of the document.

    Returns:
        list[pymupdf.Page]: The loaded PDF document pages.
    """
    pdf = get_pdf_object(document_id, pdf_lib="pymupdf")

    # Return pages without rotation to maintain coordinate consistency
    # The OCR was performed on rotated pages, but we need to account for this
    # in our coordinate transformation instead of rotating the output pages
    return list(pdf)


def _draw_bboxes_on_page(
    page: pymupdf.Page,
    page_obj: Page,
    config_id: int,
    render_scale: float = 2.0,
):
    """
    Draw bounding boxes for detections on a specific page.
    """
    # Get detections for this page and config
    detections = Detection.objects.filter(page=page_obj, config_id=config_id)

    if not detections.exists():
        logger.info(f"No detections found for page {page_obj.page_number}")
        return

    # Get page dimensions
    page_rect = page.rect
    page_width = page_rect.width
    page_height = page_rect.height

    logger.info(
        f"Page {page_obj.page_number} dimensions: {page_width}x{page_height}"
    )
    logger.info(f"Render scale: {render_scale}")

    for i, detection in enumerate(detections):
        bbox_points = detection.bbox

        # Get min/max from bbox (coordinates at original scale)
        x_coords = [point[0] for point in bbox_points]
        y_coords = [point[1] for point in bbox_points]

        # Simple scaling by render factor
        x1 = min(x_coords) * render_scale
        x2 = max(x_coords) * render_scale
        y1 = min(y_coords) * render_scale
        y2 = max(y_coords) * render_scale

        # Clamp coordinates to render bounds
        render_width = page_width * render_scale
        render_height = page_height * render_scale
        x1 = max(0, min(x1, render_width))
        x2 = max(0, min(x2, render_width))
        y1 = max(0, min(y1, render_height))
        y2 = max(0, min(y2, render_height))

        if i < 5:  # Log first few detections for debugging
            logger.debug(f"Detection {i}: '{detection.text[:20]}'")
            logger.debug(f"  Original bbox: {bbox_points}")
            logger.debug(
                f"  Render rect: ({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f})"
            )

        # Create rectangle from coordinates
        rect = pymupdf.Rect(x1, y1, x2, y2)

        # Draw rectangle (red border, no fill)
        page.draw_rect(rect, color=(1, 0, 0), width=2)

        # Add text label above the bbox
        if detection.text and len(detection.text.strip()) > 0:
            text_point = pymupdf.Point(x1, max(y1 - 10, 10))
            page.insert_text(
                text_point,
                f"{i}: {detection.text[:15]}",
                fontsize=8,
                color=(1, 0, 0),
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

        # Verify file was created
        if output_path.exists():
            logger.info(f"Successfully saved image to {output_path}")
        else:
            logger.error(f"Failed to save image to {output_path}")

        # Store relative path for URL generation
        relative_path = (
            f"ocr_results/{document_id}/{config_id}/{output_filename}"
        )
        generated_files.append(relative_path)

    return generated_files

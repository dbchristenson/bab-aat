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
    logger.info(
        f"Page {page_obj.page_number} dimensions: "
        f"{page_rect.width}x{page_rect.height}"
    )
    logger.info(f"Render scale: {render_scale}")

    page_intrinsic_rotation = page.rotation
    text_render_rotation = page_intrinsic_rotation
    inv_rotation_matrix = ~page.rotation_matrix

    for i, detection in enumerate(detections):
        bbox_points = detection.bbox

        polygon_vertices_unrotated_pdf = []
        for p_rot_coords in bbox_points:
            pt_in_rotated_frame = pymupdf.Point(
                p_rot_coords[0], p_rot_coords[1]
            )
            pt_in_unrotated_frame = pt_in_rotated_frame * inv_rotation_matrix
            polygon_vertices_unrotated_pdf.append(pt_in_unrotated_frame)

        x_coords_unrot = [p.x for p in polygon_vertices_unrotated_pdf]
        y_coords_unrot = [p.y for p in polygon_vertices_unrotated_pdf]

        # Get min/max from bbox (coordinates at original scale)
        x_coords_unrot = [p.x for p in polygon_vertices_unrotated_pdf]
        y_coords_unrot = [p.y for p in polygon_vertices_unrotated_pdf]

        rect_x1 = min(x_coords_unrot)
        rect_y1 = min(y_coords_unrot)
        rect_x2 = max(x_coords_unrot)
        rect_y2 = max(y_coords_unrot)

        drawn_rect = pymupdf.Rect(rect_x1, rect_y1, rect_x2, rect_y2)
        page.draw_rect(drawn_rect, color=(1, 0, 0), width=1)

        min_x_for_text = min(x_coords_unrot) if x_coords_unrot else 0
        min_y_for_text = min(y_coords_unrot) if y_coords_unrot else 0

        # Add text label above the bbox
        if detection.text and len(detection.text.strip()) > 0:
            text_y_offset_points = 5
            text_min_y_from_top_points = 5

            text_anchor_y = min_y_for_text - text_y_offset_points
            text_anchor_y = max(text_anchor_y, text_min_y_from_top_points)

            actual_text_point = pymupdf.Point(min_x_for_text, text_anchor_y)
            # Fontsize 8 is also in PDF points.
            page.insert_text(
                actual_text_point,
                f"{i}: {detection.text[:15]}",
                fontsize=8,
                color=(1, 0, 0),
                rotate=text_render_rotation,
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
    render_scale = 4.0

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

import io

import pymupdf
from loguru import logger

from ocr.main.utils.pdf_utils import get_pdf_object
from ocr.models import Tag


def _add_invisible_text_to_page(
    page: pymupdf.Page, tags: list, render_scale: float = 2.0
):
    """Add invisible text to a page based on tag data.

    Args:
        page: The PDF page to add text to
        tags: List of Tag objects with text and bbox data
        render_scale: Scale factor for rendering
    """
    if not tags:
        logger.info("No tags to process for this page")
        return

    inv_rotation_matrix = ~page.rotation_matrix

    for tag in tags:
        if not tag.text or not tag.bbox:
            continue

        # Transform coordinates using rotation matrix like in drawing.py
        polygon_vertices_unrotated_pdf = []
        for p_rot_coords in tag.bbox:
            pt_in_rotated_frame = pymupdf.Point(
                p_rot_coords[0], p_rot_coords[1]
            )
            pt_in_unrotated_frame = pt_in_rotated_frame * inv_rotation_matrix
            polygon_vertices_unrotated_pdf.append(pt_in_unrotated_frame)

        # Calculate bounding box dimensions
        x_coords = [p.x for p in polygon_vertices_unrotated_pdf]
        y_coords = [p.y for p in polygon_vertices_unrotated_pdf]

        rect = pymupdf.Rect(
            min(x_coords), min(y_coords), max(x_coords), max(y_coords)
        )

        # Insert invisible text
        page.add_freetext_annot(
            rect=rect,
            text=tag.text,
            opacity=0,  # Fully transparent
            align=pymupdf.TEXT_ALIGN_LEFT,
            fontsize=rect.height * 0.8,  # Scale font to fit height
            rotate=page.rotation,
        )


def export_document_to_tagged_pdf(document_id: int, config_id: int) -> bytes:
    """Export a document as a PDF with invisible searchable text.

    Args:
        document_id: ID of the document to export
        config_id: ID of the OCR config used

    Returns:
        bytes: The PDF file as bytes
    """
    # Load PDF without rotation like in drawing.py
    pdf = get_pdf_object(document_id, pdf_lib="pymupdf")

    # Create output PDF
    output_pdf = pymupdf.open()

    # Process each page
    for page_num in range(len(pdf)):
        # Get page (1-indexed for Django, 0-indexed for pymupdf)
        source_page = pdf[page_num]

        # Get tags for this page
        tags = Tag.objects.filter(
            document_id=document_id,
            detections__config=config_id,
            page_number=page_num + 1,
        ).distinct()

        # Create new page in output PDF
        output_page = output_pdf.new_page(
            width=source_page.rect.width, height=source_page.rect.height
        )

        # Copy original content
        output_page.show_pdf_page(output_page.rect, pdf, page_num)

        # Add invisible text
        _add_invisible_text_to_page(output_page, tags)

    # Save to bytes
    output_bytes = io.BytesIO()
    output_pdf.save(output_bytes)
    output_bytes.seek(0)

    return output_bytes.getvalue()

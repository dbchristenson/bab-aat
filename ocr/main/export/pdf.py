import io

import pymupdf
from loguru import logger

from ocr.main.utils.pdf_utils import get_pdf_object
from ocr.models import Tag


def _best_fit_fontsize(
    text: str,
    rect: pymupdf.Rect,
    fontname: str = "helv",
    height_fill: float = 0.8,
) -> float:
    """Start from height, then shrink to fit width if needed."""
    if not text:
        return 1.0
    size = max(rect.height * height_fill, 0.5)
    try:
        w = pymupdf.get_text_length(text, fontname=fontname, fontsize=size)
        if w > rect.width and w > 0:
            size *= rect.width / w
    except Exception as e:
        logger.warning(f"get_text_length failed: {e}")
    return max(size, 0.5)


def _add_invisible_text_to_page(page: pymupdf.Page, tags: list) -> None:
    """Add invisible (but selectable) text to a page based on tag data."""
    if not tags:
        logger.info("No tags to process for this page")
        return

    inv_rotation_matrix = ~page.rotation_matrix

    for tag in tags:
        if not tag.text or not tag.bbox:
            continue

        # Transform bbox from rotated -> intrinsic frame
        pts = []
        for x, y in tag.bbox:
            pts.append(pymupdf.Point(x, y) * inv_rotation_matrix)

        # Axis-aligned rect from quad
        x_coords = [p.x for p in pts]
        y_coords = [p.y for p in pts]
        rect = pymupdf.Rect(
            min(x_coords), min(y_coords), max(x_coords), max(y_coords)
        )

        # Height-first auto-fit with width clamp
        fontsize = _best_fit_fontsize(
            tag.text, rect, fontname="helv", height_fill=0.8
        )

        page.insert_textbox(
            rect,
            tag.text,
            fontname="helv",
            fontsize=fontsize,
            align=pymupdf.TEXT_ALIGN_LEFT,
            rotate=page.rotation,
            render_mode=3,  # invisible text layer in the content stream
        )


def export_document_to_tagged_pdf(document_id: int, config_id: int) -> bytes:
    """Export a document as a PDF with invisible searchable text."""
    pdf = get_pdf_object(document_id, pdf_lib="pymupdf")
    output_pdf = pymupdf.open()

    for page_idx in range(len(pdf)):
        source_page = pdf[page_idx]

        tags = Tag.objects.filter(
            document_id=document_id,
            detections__config_id=config_id,
            page_number=page_idx + 1,  # your DB is 1-indexed
        )

        output_page = output_pdf.new_page(
            width=source_page.rect.width,
            height=source_page.rect.height,
        )

        # Copy visual content
        output_page.show_pdf_page(output_page.rect, pdf, page_idx)

        # Add invisible, highlightable text
        _add_invisible_text_to_page(output_page, tags)

    buf = io.BytesIO()
    # Smaller, cleaner PDFs
    output_pdf.save(buf, deflate=True, garbage=3)
    buf.seek(0)
    return buf.getvalue()

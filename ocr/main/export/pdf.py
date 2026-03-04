import io

import pymupdf
from loguru import logger

from ocr.main.utils.pdf_utils import get_pdf_object
from ocr.models import Tag


def _best_fit_fontsize(
    text: str,
    rect: pymupdf.Rect,
    fontname: str = "helv",
) -> float:
    """Pick the largest fontsize that fits inside *rect*.

    pymupdf's ``insert_textbox`` silently discards text when even the first
    line overflows vertically.  The effective line-height is roughly
    ``fontsize * 1.67`` for base-14 fonts, so the max fontsize that fits a
    rect of height *h* is approximately ``h / 1.67``.  We use ``h * 0.55``
    (≈ ``h / 1.82``) as a safe starting point, then clamp to the rect width.
    """
    if not text:
        return 1.0

    size = max(rect.height * 0.55, 0.5)

    try:
        w = pymupdf.get_text_length(text, fontname=fontname, fontsize=size)
        if w > rect.width and w > 0:
            size *= rect.width / w
    except Exception as e:
        logger.warning(f"get_text_length failed: {e}")

    return max(size, 0.5)


def _add_invisible_text_to_page(
    page: pymupdf.Page,
    tags: list,
    ocr_rotated: bool = False,
    page_height_pts: float = 0,
) -> int:
    """Add invisible (but selectable/searchable) text to a page.

    Args:
        page: The pymupdf page to add text to.
        tags: List of Tag objects with text and bbox.
        ocr_rotated: True if this page was rotated to landscape during OCR
            (portrait page with no built-in /Rotate).
        page_height_pts: Original page height in points (needed when
            ocr_rotated is True to undo the coordinate transformation).

    Returns:
        Number of tags successfully written.
    """
    if not tags:
        return 0

    count = 0
    for tag in tags:
        if not tag.text or not tag.bbox:
            continue

        pts = []
        for x, y in tag.bbox:
            if ocr_rotated:
                # During OCR, pypdfium2 rotated this portrait page 270 deg CW
                # (set_rotation(270)) to make it landscape. The stored bbox
                # coords are in that rotated space. Undo the rotation so
                # coordinates map to the original portrait orientation.
                x, y = y, page_height_pts - x
            pts.append(pymupdf.Point(x, y))

        x_coords = [p.x for p in pts]
        y_coords = [p.y for p in pts]
        rect = pymupdf.Rect(
            min(x_coords), min(y_coords), max(x_coords), max(y_coords)
        )

        if rect.is_empty or rect.is_infinite:
            logger.warning(
                f"Skipping tag '{tag.text}': invalid rect {rect}"
            )
            continue

        fontsize = _best_fit_fontsize(tag.text, rect)

        rc = page.insert_textbox(
            rect,
            tag.text,
            fontname="helv",
            fontsize=fontsize,
            align=pymupdf.TEXT_ALIGN_LEFT,
            render_mode=3,
        )

        if rc < 0:
            logger.debug(
                f"Text overflow for '{tag.text}' "
                f"(rc={rc:.1f}, size={fontsize:.2f}, rect={rect})"
            )
        count += 1

    return count


def export_document_to_tagged_pdf(document_id: int, config_id: int) -> bytes:
    """Export a document as a PDF with invisible searchable text.

    Modifies the source PDF directly — this preserves all original features
    (links, annotations, bookmarks) and avoids issues with show_pdf_page
    content copying.
    """
    pdf = get_pdf_object(document_id, pdf_lib="pymupdf")

    total_tags = 0
    for page_idx in range(len(pdf)):
        page = pdf[page_idx]

        tags = list(
            Tag.objects.filter(
                document_id=document_id,
                detections__config_id=config_id,
                page_number=page_idx + 1,
            ).distinct()
        )

        logger.info(
            f"[export] page {page_idx + 1}/{len(pdf)}: "
            f"{len(tags)} tags, "
            f"size={page.rect.width:.0f}x{page.rect.height:.0f}, "
            f"rotation={page.rotation}"
        )

        if not tags:
            continue

        # Detect pages that were rotated to landscape during OCR.
        # The OCR pipeline (page_to_img.rotate_landscape) rotates portrait
        # pages 270 deg CW via pypdfium2 before rendering. That rotation is
        # ephemeral (not saved to the PDF), so the stored tag bboxes are in
        # the rotated coordinate space. We need to undo that here.
        mb = page.mediabox
        ocr_rotated = page.rotation == 0 and mb.height > mb.width

        if ocr_rotated:
            logger.info(
                f"[export] page {page_idx + 1} is portrait "
                f"({mb.width:.0f}x{mb.height:.0f}) — "
                "undoing OCR rotation for tag coords"
            )

        added = _add_invisible_text_to_page(
            page,
            tags,
            ocr_rotated=ocr_rotated,
            page_height_pts=mb.height if ocr_rotated else 0,
        )
        total_tags += added

    logger.info(
        f"[export] done: wrote {total_tags} tags across {len(pdf)} pages"
    )

    buf = io.BytesIO()
    pdf.save(buf, deflate=True, garbage=0)
    pdf.close()
    buf.seek(0)

    tagged_bytes = buf.getvalue()

    # Quick sanity check: re-open and verify text is extractable
    verify = pymupdf.open(stream=tagged_bytes, filetype="pdf")
    sample_text = ""
    for i in range(min(3, len(verify))):
        sample_text += verify[i].get_text()
    verify.close()

    if total_tags > 0 and not sample_text.strip():
        logger.warning(
            "[export] tags were inserted but no text is extractable — "
            "this may indicate a pymupdf issue"
        )
    else:
        logger.info(
            f"[export] verification OK: "
            f"{len(sample_text)} chars extractable from first pages"
        )

    return tagged_bytes

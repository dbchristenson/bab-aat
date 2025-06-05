from typing import Union

import pymupdf
import pypdfium2 as pdfium


def rotate_landscape(
    page: Union[pdfium.PdfPage, pymupdf.Page], pdf_lib: str = "pypdfium2"
) -> Union[pdfium.PdfPage, pymupdf.Page]:
    """
    This function rotates the page into landscape orientation.
    """
    if pdf_lib == "pymupdf":
        # For pymupdf, get page dimensions using rect
        rect = page.rect
        p_w, p_h = rect.width, rect.height

        # Check if page is in portrait orientation and rotate if needed
        if p_h > p_w:
            # Rotate 90 degrees counterclockwise to make it landscape
            page.set_rotation(90)

    elif pdf_lib == "pypdfium2":
        # For pypdfium2, use the original logic
        p_w, p_h = page.get_size()
        if p_h > p_w:
            page.set_rotation(270)

    return page

from typing import Union

import PIL as pil
import pypdfium2 as pdfium
from PIL import ImageOps

try:
    import pymupdf
except ImportError:
    pymupdf = None


def rotate_landscape(
    page: Union[pdfium.PdfPage, "pymupdf.Page"], pdf_lib: str = "pypdfium2"
) -> Union[pdfium.PdfPage, "pymupdf.Page"]:
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


def create_img_and_pad_divisible_by_32(
    page: pdfium.PdfPage, scale: int = 2
) -> pil.Image:
    """
    This function takes a page and scales it by the given scale factor to
    improve resolution. It then pads the image to make its width and height
    divisible by 32.
    """
    # Rotate the page into landscape orientation if needed
    page = rotate_landscape(page, pdf_lib="pypdfium2")

    # Render the page with the given scale
    bitmap = page.render(scale=scale)

    w_remainder = bitmap.width % 32
    h_remainder = bitmap.height % 32

    w_to_pad = 0
    h_to_pad = 0

    # Calculate the padding needed to make the width and height divisible by 32
    if w_remainder != 0:
        k = 32 - w_remainder
        w_to_pad += k
    if h_remainder != 0:
        k = 32 - h_remainder
        h_to_pad += k

    # Convert the bitmap to a PIL image and pad it
    img = bitmap.to_pil()
    padded_img = ImageOps.expand(
        img, border=(0, 0, w_to_pad, h_to_pad), fill="black"
    )  # noqa E501

    page.close()

    return padded_img

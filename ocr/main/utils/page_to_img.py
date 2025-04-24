import PIL as pil
import pypdfium2 as pdfium
from PIL import ImageOps


def rotate_landscape(page: pdfium.PdfPage) -> pdfium.PdfPage:
    """
    This function rotates the page into landscape orientation.
    """
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
    page = rotate_landscape(page)

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
    )

    page.close()

    return padded_img


def crop_out_figure(img: pil.Image) -> pil.Image:
    """
    This function crops the image to get only the figure part of the image.
    The figure is assumed to
    """

    return


def crop_out_table(img: pil.Image) -> pil.Image:
    """
    This functions crops the image to get only the table part
    of the image.
    """

    return

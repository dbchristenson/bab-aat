import cv2 as cv
import numpy as np
from loguru import logger

from ocr.main.utils.page_to_img import rotate_landscape
from ocr.models import Document


def get_pdf_object(document_id: int, pdf_lib: str = "pypdfium2"):
    """
    Get the PDF document object for a given document ID.

    Args:
        document_id (int): The ID of the document.

    Returns:
        PdfDocument: The PDF document object.
    """
    logger.info(f"Fetching document with ID: {document_id} for PDF object")
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(
            f"Document with ID {document_id} not found in _get_pdf_object."
        )
        raise

    try:
        with document.file.open("rb") as f:  # Open in binary read mode
            pdf_bytes = f.read()

        logger.info(f"Read {len(pdf_bytes)} bytes from document {document_id}")

        if pdf_lib == "pymupdf":
            import pymupdf

            pdf = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        elif pdf_lib == "pypdfium2":
            from pypdfium2 import PdfDocument

            pdf = PdfDocument(pdf_bytes)  # Load from bytes

        logger.info(f"Successfully loaded PDF for document {document_id}")
        return pdf
    except Exception as e:
        logger.error(
            f"Error opening or loading PDF for document {document_id}: {e}",
            exc_info=True,
        )
        raise


def page_to_image(page_obj, page_render_scale: float = 4.0):
    """
    Convert a PDF page object to an image.

    Args:
        page_obj: The PDF page object.
        page_render_scale (float): Scale factor for rendering the page.

    Returns:
        PIL.Image: The rendered image of the page.
    """
    # Only rotate if page is in portrait orientation (height > width)
    page_obj = rotate_landscape(page_obj, pdf_lib="pypdfium2")
    page_bitmap = page_obj.render(scale=page_render_scale)
    page_pil = page_bitmap.to_pil()
    image_np = np.array(page_pil)

    if len(image_np.shape) == 3:
        if image_np.shape[2] == 3:  # RGB
            gray_image_np = cv.cvtColor(image_np, cv.COLOR_RGB2GRAY)
        elif image_np.shape[2] == 4:  # RGBA
            gray_image_np = cv.cvtColor(image_np, cv.COLOR_RGBA2GRAY)
        else:  # Should not happen with typical PIL images from PDF
            gray_image_np = image_np  # Fallback, but unlikely
    else:  # Already grayscale or single channel
        gray_image_np = image_np

    return gray_image_np

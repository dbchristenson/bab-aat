import logging
import os

from django.core.files import File

from babaatsite.settings import MEDIA_ROOT
from ocr.main.intake.pdf_img_pipeline import save_document
from ocr.main.utils.loggers import basic_logging
from ocr.models import Document, Vessel

basic_logging(__name__)


def handle_pdf(file: File, vessel_obj: Vessel) -> None:
    """
    Handle the uploaded PDF file. This function processes the PDF file,
    creates a Document object, and saves the PDF file to the server.
    It also creates Page objects for each page in the PDF and saves
    images of the pages to the server.

    Args:
        file (File): The uploaded PDF file.
        vessel_obj (Vessel): The Vessel object associated with the document.
    """
    return


def handle_zip(file: File, vessel_obj: Vessel) -> None:
    """
    Unzips the uploaded ZIP file to the media directory and processes each PDF
    file.
    """
    return


def get_pdf_file_objects(directory_path: str) -> list[File]:
    """
    Walks through the given directory (and subdirectories) and returns a list
    of Django File objects for every PDF file found.

    Args:
        directory_path (str): The path to the PDF files' directory.

    Returns:
        List[File]: A list of Django File objects wrapping each PDF file.
    """
    pdf_files = []
    # Recursively walk the directory
    for root, dirs, files in os.walk(directory_path):
        for filename in files:
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(root, filename)
                # Open the file in binary mode
                f = open(file_path, "rb")
                # Wrap it in Django's File object
                # (remember, the caller must later close it)
                django_file = File(f, name=filename)
                pdf_files.append(django_file)
    return pdf_files


def handle_uploaded_file(file: File, vessel_id: int) -> None:
    """
    Handle the uploaded file. This function processes the uploaded file,
    which may be a pdf or a zip file. From a pdf, it creates a document
    and page objects. From a zip file, it extracts the pdfs and populates
    the Document table with the pdfs and then populates the Page table
    with images of the pdfs' pages. Finally we also create detections
    for each new page we create.


    Args:
        file (File): The uploaded file.
        vessel_id (int): The ID of the vessel associated with the document.
    """
    vessel_obj = Vessel.objects.get(id=vessel_id)
    file_ext = file.name.split(".")[-1].lower()  # Apparently this is not safe
    logging.warning(
        "Collecting file extension using potentially vulnerable method in handle_upload.py"  # noqa 501
    )

    upload_directory = os.path.join(MEDIA_ROOT, "documents")
    os.makedirs(upload_directory, exist_ok=True)

    # Save file, pages to the server
    if file_ext == "pdf":
        handle_pdf(file, vessel_obj)
    else:
        handle_zip(file, vessel_obj)

    # OCR Inference on the pages
    # TODO

    return

import logging
import os

from celery import shared_task
from django.core.files import File
from django.db import IntegrityError

from babaatsite.settings import MEDIA_ROOT
from ocr.main.intake.pdf_img_pipeline import convert_pdf, save_document
from ocr.main.utils.loggers import basic_logging
from ocr.models import Document, Vessel

basic_logging(__name__)


def handle_pdf(file: File, vessel_obj: Vessel | None, output: str) -> None:
    """
    Handle the uploaded PDF file. This function processes the PDF file,
    creates a Document object, and saves the PDF file to the server.
    It also creates Page objects for each page in the PDF and saves
    images of the pages to the server.

    Args:
        file (File): The uploaded PDF file.
        vessel_obj (Vessel): The Vessel object associated with the document.
        output (str): The output directory where the PDF and images are saved.
    """
    try:
        document_id = save_document(file, vessel_obj)
    except IntegrityError as e:
        logging.error(f"Error saving document '{file.name}': {e}")
        raise

    # If document_id == None then the document was already saved
    # and has been processed. We don't need to do anything else.
    if not document_id:
        logging.info(
            f"Document '{file.name}' already exists. No further processing required."  # noqa 501
        )
        return

    document = Document.objects.get(id=document_id)

    upload_directory = os.path.join(MEDIA_ROOT, "pages")
    os.makedirs(upload_directory, exist_ok=True)

    convert_pdf(file, document, upload_directory, scale=4)

    return document_id


@shared_task(bind=True)
def process_pdf_task(self, disk_path: str, vessel_id: int, output_dir: str):
    """
    Celery task wrapper for handling pdfs
    """
    vessel = Vessel.objects.get(id=vessel_id)
    with open(disk_path, "rb") as f:
        django_file = File(f, name=os.path.basename(disk_path))
        handle_pdf(django_file, vessel, output_dir)

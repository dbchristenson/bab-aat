import logging
import os

from celery import shared_task
from django.core.files import File
from django.db import IntegrityError

from ocr.main.intake.document_ingestion import save_document
from ocr.main.utils.loggers import basic_logging

basic_logging(__name__)


def handle_pdf(file: File, vessel_id: int) -> None:
    """
    Handle the uploaded PDF file. This function processes the PDF file,
    creates a Document object, and saves the PDF file to the server.

    Args:
        file (File): The uploaded PDF file.
        vessel_id (int): The ID of the Vessel associated with the document.
    """
    try:
        document_id = save_document(file, vessel_id)
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

    return document_id


@shared_task(bind=True, ignore_result=True)
def process_pdf_task(self, disk_path: str, vessel_id: int):
    """
    Celery task wrapper for handling pdfs

    Args:
        disk_path (str): The path to the PDF file on disk.
        vessel_id (int): The ID of the Vessel associated with the document.
    """
    with open(disk_path, "rb") as f:
        django_file = File(f, name=os.path.basename(disk_path))
        handle_pdf(django_file, vessel_id)


@shared_task(bind=True, ignore_result=False)
def get_document_detections(self, document_id: int, config_path: str):
    """
    Celery task to get detections for a document.

    Args:
        document_id (int): The ID of the document to process.
        config_path (str): The path to the config file for the OCR model.
    """
    from ocr.main.inference.detections import analyze_document

    logging.info(f"Starting detection for document {document_id}")

    analyze_document(
        document_id=document_id,
        config_path=config_path,
    )

import logging
import os

from celery import shared_task
from django.core.files import File
from django.db import IntegrityError
from paddleocr import PaddleOCR

from ocr.main.intake.document_ingestion import save_document
from ocr.main.utils.loggers import basic_logging

basic_logging(__name__)


# Document Intake
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


# OCR Detections
_ocr_model_cache = {}


def _initialize_paddle_ocr(config_id: int) -> PaddleOCR:
    """
    This function handles the actual initalization of the PaddleOCR
    object. The goal of the function is to cache the PaddleOCR object
    so that it is not re-initialized for every task call.

    Args:
        config_id (int): The ID of the OCRConfig object to use.

    Returns:
        PaddleOCR: The initialized PaddleOCR object.
    """
    from ocr.models import OCRConfig

    logging.info(f"Attempting to init PaddleOCR for config_id: {config_id}")

    try:
        ocr_django_config = OCRConfig.objects.get(pk=config_id)
        paddle_params = ocr_django_config.config

        if not isinstance(paddle_params, dict):
            logging.error(
                f"Config field for OCRConfig ID {config_id} is not a valid "
                f"dictionary. Found: {paddle_params}"
            )
            # Handle error: raise an exception or return a default model
            raise ValueError(f"Invalid OCR params for config_id {config_id}")

        # Ensure 'show_log' is explicitly managed if not in stored config,
        # to prevent excessive PaddleOCR logging.
        if "show_log" not in paddle_params:
            paddle_params["show_log"] = False  # Default to False

        model = PaddleOCR(**paddle_params)
        logging.info(f"Successfully init PaddleOCR for config_id: {config_id}")
        return model
    except OCRConfig.DoesNotExist:
        logging.error(f"OCRConfig with ID {config_id} does not exist.")
        # Handle error: raise an exception or return a default model
        raise
    except Exception as e:
        logging.error(
            f"Failed to init PaddleOCR model for config_id {config_id}: {e}",
            exc_info=True,
        )
        raise

    return


def get_ocr_model_instance(config_id: int) -> PaddleOCR:
    """
    Retrieves a PaddleOCR model instance from cache or initializes it.
    """
    if config_id not in _ocr_model_cache:
        logging.info(f"OCR model for config_id '{config_id}' not in cache.")
        _ocr_model_cache[config_id] = _initialize_paddle_ocr(config_id)
    else:
        logging.info(f"Reusing cached OCR model for config_id '{config_id}'.")
    return _ocr_model_cache[config_id]


@shared_task(bind=True, ignore_result=False)
def get_document_detections(self, document_id: int, config_id: int):
    """
    Celery task to get detections for a document.

    Args:
        document_id (int): The ID of the document to process.
        config_path (str): The path to the config file for the OCR model.
    """
    from ocr.main.inference.detections import analyze_document

    logging.info(f"Starting detection for document {document_id}")
    logging.info(f"Using config id: {config_id}")

    analyze_document(
        document_id=document_id,
        ocr=get_ocr_model_instance(config_id),
        config_id=config_id,
    )

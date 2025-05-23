import os

from celery import shared_task
from django.core.files import File
from django.db import IntegrityError
from loguru import logger
from paddleocr import PaddleOCR

from ocr.main.inference.postprocessing.handler import (
    run_postprocessing_pipeline,
)
from ocr.main.intake.document_ingestion import save_document


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
        logger.error(f"Error saving document '{file.name}': {e}")
        raise

    if not document_id:
        logger.info(
            f"Document '{file.name}' already exists. "
            f"No further processing required."
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

    logger.info(f"Attempting to init PaddleOCR for config_id: {config_id}")

    try:
        ocr_django_config = OCRConfig.objects.get(pk=config_id)
        paddle_params = ocr_django_config.config

        if not isinstance(paddle_params, dict):
            logger.error(
                f"Config field for OCRConfig ID {config_id} is not a valid "
                f"dictionary. Found: {paddle_params}"
            )
            raise ValueError(f"Invalid OCR params for config_id {config_id}")

        if "show_log" not in paddle_params:
            paddle_params["show_log"] = False

        if "paddle" in paddle_params:
            paddle_params = paddle_params["paddle"]

        model = PaddleOCR(**paddle_params)
        logger.info(f"Successfully init PaddleOCR for config_id: {config_id}")
        return model
    except OCRConfig.DoesNotExist:
        logger.error(f"OCRConfig with ID {config_id} does not exist.")
        raise
    except Exception as e:
        logger.error(
            f"Failed to init PaddleOCR model for config_id {config_id}: {e}",
            exc_info=True,
        )
        raise


def _get_ocr_model_instance(config_id: int) -> PaddleOCR:
    """
    Retrieves a PaddleOCR model instance from cache or initializes it.
    """
    if config_id not in _ocr_model_cache:
        logger.info(f"OCR model for config_id '{config_id}' not in cache.")
        _ocr_model_cache[config_id] = _initialize_paddle_ocr(config_id)
    else:
        logger.info(f"Reusing cached OCR model for config_id '{config_id}'.")
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

    logger.info(f"Starting detection for document {document_id}")
    logger.info(f"Using config id: {config_id}")

    analyze_document(
        document_id=document_id,
        ocr=_get_ocr_model_instance(config_id),
        config_id=config_id,
    )


# Post-processing
@shared_task(bind=True, ignore_result=False)
def process_detections_to_tags(self, document_id: int):
    """
    Celery task for processing detections to tags.

    Post-processing pipeline for a single document begins here.
    The function will call a handler which will use the detections
    from the given document and use an algorithm (likely multiple)
    to refine the detections into tags. Those tags will then be saved
    to the database.

    Args:
        document_id (int): The ID of the document to process.

    Returns:
        None
    """
    logger.info(f"Initiated detection -> tag task for document {document_id}")

    try:
        # The handler will fetch detections and save tags
        run_postprocessing_pipeline(document_id=document_id)
        logger.info(
            f"Completed post-processing for document_id: {document_id}"
        )
    except Exception as e:
        logger.error(
            f"Error during post-processing for document_id: {document_id}."
            f"Error: {e}",
            exc_info=True,
        )
        raise

    return


# Export
@shared_task(bind=True, ignore_result=False)
def export_tags_from_document(self, document_id: int):
    """
    Celery task for exporting tags from a document.

    This task can only be called on documents that have tags associated
    with them. The function basically queries the database for the tags
    related to the document and then organizes them into a denormalized
    table format. Each row in the table will represent a tag and its
    associated data. Therefore the document number will be repeated
    for each tag. This is inline with BAB's general document control
    strategy.

    This function may be used on its own or as part of a batch export
    process. The function will return a CSV file containing the tags
    and their associated data. It is expected for the user to download
    the file from the server.

    Args:
        document_id (int): The ID of the document to export tags from.

    Returns:
        The path to the CSV file containing the tags and their associated data.
    """
    return


@shared_task(bind=True, ignore_result=False)
def export_annotated_document(self, document_id: int):
    """
    Celery task for exporting an annotated document.

    This task can only be called on documents that have tags associated
    with them. The function will call a handler which will write the tags
    of the document on to the PDF file at the detection location using
    bounding box coordinates. The text will be invisible.

    This function may be used on its own or as part of a batch export
    process. The function will return a PDF file containing the
    annotations and their associated data. It is expected for the user
    to download the file(s) from the server.

    Args:
        document_id (int): The ID of the document to export tags from.

    Returns:
        The path to the reconstructed PDF file.
    """
    return

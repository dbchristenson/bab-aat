from loguru import logger

from ocr.main.utils.task_helpers import _chunk_and_dispatch_tasks
from ocr.models import Document
from ocr.tasks import get_document_detections as get_document_detections_task

# Define a default chunk size for dispatching tasks
CHUNK_SIZE = 20


def handle_batch_document_detections(
    vessel_id: int, department_origin: str, config_id: int
) -> list:
    """
    Queries documents based on vessel ID and department origin,
    then dispatches OCR detection tasks for them in chunks using the
    specified config ID.

    Args:
        vessel_id (int): The ID of the Vessel to filter documents by.
        department_origin (str): The department origin code to filter
                                 documents by.
        config_id (int): The ID of the OCRConfig to use for detection.

    Returns:
        list: A list of task IDs for the dispatched Celery tasks.
              Returns an empty list if no documents are found or if an
              error occurs.
    """
    logger.info(
        f"Initiating batch document detections for vessel_id: {vessel_id}, "
        f"department_origin: '{department_origin}', config_id: {config_id}"
    )

    try:
        # Query for documents matching the criteria
        documents_qs = Document.objects.filter(
            vessel_id=vessel_id, department_origin=department_origin
        )
        document_ids = list(documents_qs.values_list("id", flat=True))

        if not document_ids:
            logger.info(
                f"No documents found matching vessel_id: {vessel_id} and "
                f"department_origin: '{department_origin}'."
            )
            return None

        logger.info(
            f"Found {len(document_ids)} documents. Dispatching OCR "
            f"detection tasks in chunks of {CHUNK_SIZE} using "
            f"config_id: {config_id}."
        )

        # Dispatch tasks in chunks
        # The `get_document_detections_task` expects `document_id` (as `item`
        # from the list) and `config_id` (as a keyword argument).
        task_ids = _chunk_and_dispatch_tasks(
            items=document_ids,
            task_to_run=get_document_detections_task.delay,
            chunk_size=CHUNK_SIZE,
            config_id=config_id,  # Passed as kwarg to Celery task
        )

        logger.info(
            f"Successfully dispatched {len(task_ids)} Celery tasks for "
            f"batch OCR detection."
        )
        return task_ids

    except Exception as e:
        logger.error(
            f"An error occurred during batch document detection handling for "
            f"vessel_id: {vessel_id}, department_origin: "
            f"'{department_origin}', config_id: {config_id}. Error: {e}",
            exc_info=True,
        )
        # Depending on how you want to handle errors in the calling view,
        return []

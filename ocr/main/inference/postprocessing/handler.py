import pipeline_steps as ps
from loguru import logger

from ocr.models import Detection, Document, Tag


def _handle_no_detections():
    """
    Handle the case where no detections are found.
    """
    logger.info("No detections found. Skipping postprocessing.")

    return None


def run_postprocessing_pipeline(document_id: int):
    """
    placeholer
    """
    logger.info(f"Running postprocessing pipeline for document {document_id}")
    document = Document.objects.get(id=document_id)  # should always exist
    detections: list[Detection] = Detection.objects.filter(document=document)

    if not detections.exists():
        return _handle_no_detections()

    for det in detections:
        text = det.text
        bbox = det.bbox
        confidence = det.confidence
        config = det.config
        paddle_params = config["paddle"]
        scale_param = config["scale"]

    return None

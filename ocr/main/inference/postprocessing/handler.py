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
    Placeholder for the postprocessing pipeline.
    """
    logger.info(f"Running postprocessing pipeline for document {document_id}")
    detections: list[Detection] = Detection.objects.filter(
        page__document_id=document_id
    )

    if not detections.exists():
        return _handle_no_detections()

    for det in detections:
        unscaled_bbox = ps._rescale_bbox(det.bbox, det.config.config["scale"])

    return None

from loguru import logger

from ocr.main.inference.postprocessing.pipeline_steps import (
    merge_touching_detections,
    remove_numeric_only_tags,
    remove_single_character_detections,
    spell_check_tags,
)
from ocr.models import Detection, Tag


def _handle_no_detections():
    """
    Handle the case where no detections are found.
    """
    logger.info("No detections found. Skipping postprocessing.")

    return None


def _save_tags(tag_data: list[tuple[Tag, list[Detection]]]):
    """
    Save the tags to the database.
    """
    from django.db import transaction

    if not tag_data:
        logger.info("No tags to save.")
        return

    for tag, detections in tag_data:
        try:
            with transaction.atomic():
                tag.resolve_is_equipment_tag()
                tag.save()
                for detection in detections:
                    detection.tag = tag
                    detection.save(update_fields=["tag"])
                logger.info(
                    f"Saved tag: {tag.text} for document {tag.document.name}"
                )
        except Exception as e:
            logger.error(f"Error saving tag {tag.id}: {e}")


def run_postprocessing_pipeline(document_id: int):
    """
    Placeholder for the postprocessing pipeline.
    """
    logger.info(f"Running postprocessing pipeline for document {document_id}")
    detections: list[Detection] = Detection.objects.filter(
        page__document_id=document_id
    )

    # Delete all existing tags for the document
    Tag.objects.filter(document_id=document_id).delete()

    if not detections.exists():
        return _handle_no_detections()

    tag_det_data = merge_touching_detections(detections)
    tag_det_data = remove_single_character_detections(tag_det_data)
    tag_det_data = remove_numeric_only_tags(tag_det_data)
    tag_det_data = spell_check_tags(tag_det_data)

    return _save_tags(tag_det_data)

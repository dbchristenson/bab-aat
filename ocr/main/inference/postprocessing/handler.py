from loguru import logger

from ocr.main.inference.postprocessing.pipeline_steps import (
    merge_touching_detections,
    remove_numeric_only_tags,
    remove_single_character_detections,
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
                    logger.debug(  # Add this log
                        f"Before saving detection link: Det obj_id={id(detection)}, "
                        f"pk={detection.pk}, text='{detection.text}', "
                        f"tag_to_link_pk={tag.pk}"
                    )
                    detection.tag = tag
                    if detection.pk is None:
                        logger.error(
                            f"CRITICAL: Detection PK is None before save! Det: {detection}"
                        )
                        # Fallback to full save if PK is None for some reason
                        detection.save()
                    else:
                        detection.save(update_fields=["tag"])
                    logger.debug(
                        f"Linked detection {detection.id} to tag {tag.id}"
                    )
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

    # Convert to a list to make sure we're dealing with instances
    # and to inspect them easily.
    initial_detections_list = list(detections)
    logger.info(
        f"Fetched {len(initial_detections_list)} detections initially."
    )

    # Log info for the first few detections
    for i, det in enumerate(initial_detections_list[:3]):  # Log first 3
        logger.debug(
            f"Initial Det[{i}]: obj_id={id(det)}, pk={det.pk}, text='{det.text}'"
        )

    if not detections.exists():
        return _handle_no_detections()

    tag_det_data = merge_touching_detections(detections)
    tag_det_data = remove_single_character_detections(tag_det_data)
    tag_det_data = remove_numeric_only_tags(tag_det_data)

    if tag_det_data:
        for i, (tag, dets_in_tuple) in enumerate(
            tag_det_data[:1]
        ):  # Inspect first tag group
            logger.debug(
                f"Tag before save: obj_id={id(tag)}, text='{tag.text}'"
            )
            for j, det_in_group in enumerate(
                dets_in_tuple[:3]
            ):  # First 3 dets in this group
                logger.debug(
                    f"  Det in group for Tag[{i}], Det[{j}]: "
                    f"obj_id={id(det_in_group)}, pk={det_in_group.pk}, text='{det_in_group.text}'"
                )

    return _save_tags(tag_det_data)

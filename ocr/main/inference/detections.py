import gc

import numpy as np
from loguru import logger

from ocr.main.inference.preprocessing.boundaries import figure_table_extraction
from ocr.main.utils.pdf_utils import get_pdf_object, page_to_image
from ocr.models import Detection, Page


def _build_detection_list(
    results, page_id: int, config_id: int, min_confidence: float = 0.6
) -> list[Detection]:
    """
    Helper function for _extract_detections_from_image to build a list
    of Detection objects.

    Args:
        results: Results object from the OCR network.
        page_id (int): The ID of the Page object this image belongs to.
        config_id (int): The ID of the OCRConfig object used.

    Returns:
        list[Detection]: List of Detection objects created from the OCR.
    """
    # Our predictions come from images so len(results) = 1
    result_dict = results[0]

    detections = []
    for text, score, bbox in zip(
        result_dict["rec_texts"],
        result_dict["rec_scores"],
        result_dict["rec_polys"],
    ):
        if score < min_confidence:  # Default minimum confidence threshold
            continue

        det = Detection(
            page_id=page_id,
            bbox=bbox,
            confidence=score,
            text=text,
            config_id=config_id,
        )
        detections.append(det)

    return detections


def _extract_detections_from_image(
    image_np: np.ndarray,
    # ocr,
    paddle_config: dict,
    config_id: int,
    page_db_id: int,
    min_confidence: float = 0.6,
) -> list[Detection]:
    """
    Get detections for a given image numpy array using the OCR network.
    Enhanced with granular memory monitoring and immediate cleanup.

    Args:
        image_np (np.ndarray): The image numpy array to process.
        ocr (PaddleOCR): The configured OCR network.
        config_id (int): The id of the OCRConfig object used.
        page_db_id (int): The ID of the Page object this image belongs to.
        min_confidence (float): Minimum confidence threshold for detections.

    Returns:
        list[Detection]: List of detection objects for the image.
    """
    import modal

    logger.info(f"Starting OCR session for page {page_db_id}...")
    logger.debug(f"image_np shape, dtype: {image_np.shape}, {image_np.dtype}")

    # Ensure image has 3 channels (RGB) as expected by PaddleOCR
    if len(image_np.shape) == 2:
        logger.debug("Converting 2D grayscale image to 3-channel RGB")
        image_np = np.stack([image_np] * 3, axis=2)
        logger.debug(f"After conversion, shape: {image_np.shape}")
    elif len(image_np.shape) == 3 and image_np.shape[2] == 1:
        logger.debug("Converting single-channel image to 3-channel RGB")
        image_np = np.repeat(image_np, 3, axis=2)
        logger.debug(f"After conversion, shape: {image_np.shape}")

    try:
        logger.debug(f"Getting modal function for page {page_db_id}")
        ocr_fn = modal.Function.from_name("modal-ocr", "ocr_inference")

        logger.debug(f"Calling remote OCR function for page {page_db_id}")
        ocr_results = ocr_fn.remote(
            im_numpy=image_np, config_id=config_id, paddle_config=paddle_config
        )

        logger.debug(f"Checking OCR results for page {page_db_id}")
        if not ocr_results or not ocr_results[0]:
            logger.info(f"[{config_id}] No OCR results for page {page_db_id}")
            return []

        logger.debug(f"Building detection list for page {page_db_id}")
        detections = _build_detection_list(
            ocr_results, page_db_id, config_id, min_confidence
        )

        logger.debug(
            f"Successfully processed {len(detections)} detections for page "
            f"{page_db_id}"
        )
        return detections

    except Exception as e:
        import traceback

        tb_str = traceback.format_exc()
        logger.error(
            f"Error in OCR processing for page {page_db_id}: {e}\n"
            f"Full traceback:\n{tb_str}",
            exc_info=True,
        )
        return []

    # Clean up
    finally:
        try:
            # Only try to delete ocr_results if it was successfully created
            if "ocr_results" in locals() and ocr_results is not None:
                del ocr_results

            gc.collect()

        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")


def _adjust_and_save_detections(
    detections: list[Detection],
    offset_x: int,
    offset_y: int,
    page_render_scale: float,
) -> list[Detection]:
    """
    Adjusts the bbox coordinates of detections and saves them.

    We have two adjustments to make to the bbox:
    1. Add the offset_x and offset_y to each point in the bbox.
    2. Rescale the bbox points using the page_render_scale factor.

    Because we scale the page to a higher resolution for rendering,
    we need to adjust the bbox points accordingly to match the original
    dimensions.

    The bboxes are in the format [[x1,y1],[x2,y2],[x3,y3],[x4,y4]].

    Args:
        detections (list[Detection]): List of raw detection objects.
        offset_x (int): The x-coordinate offset to add to bbox points.
        offset_y (int): The y-coordinate offset to add to bbox points.
        page_render_scale (float): Upscaling factor for getting detections.

    Returns:
        list[Detection]: List of saved detection objects with adjusted bboxes.
    """
    saved_detections = []
    for det in detections:
        logger.debug(det.bbox)
        logger.debug(type(det.bbox))
        logger.debug(np.array(det.bbox).shape)
        logger.debug(np.array(det.bbox)[0])
        # Adjust poly: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        adjusted_bbox = [[p[0] + offset_x, p[1] + offset_y] for p in det.bbox]
        # Rescale bbox points
        adjusted_bbox = [
            [p[0] / page_render_scale, p[1] / page_render_scale]
            for p in adjusted_bbox
        ]
        det.bbox = adjusted_bbox
        det.save()
        saved_detections.append(det)
        logger.debug(
            f"[{det.config.name}] Saved detection ID {det.id} for page ID {det.page_id} with adjusted bbox: {det.bbox}"  # noqa E501
        )
    return saved_detections


def _create_page_in_db(document_id: int, page_number: int) -> Page:
    """
    Create a Page object in the database for a given doc ID and page number.
    If the Page object already exists, it will not be created again.

    Args:
        document_id (int): The ID of the document.
        page_number (int): The page number (0-indexed).

    Returns:
        Page: The Page object created or retrieved from the database.
    """
    page_db, created = Page.objects.get_or_create(
        document_id=document_id, page_number=page_number
    )

    if created:
        logger.info(
            f"Created Page object for doc {document_id}, page {page_number}"
        )

    return page_db


def analyze_document(
    document_id: int,
    # ocr,
    config_id: int,
    figure_kwargs: dict = None,
    table_kwargs: dict = None,
    boundary_preprocessing: bool = False,
) -> list[Detection]:
    """
    Analyze a document by processing each page, extracting figure and table
    regions, performing OCR on these regions, and saving adjusted detections.

    Args:
        document_id (int): The ID of the document to analyze.
        #ocr (PaddleOCR): The configured OCR network.
        config_id (int): The ID of the OCRConfig object used.
        figure_kwargs (dict, optional): Arguments for figure extraction.
        table_kwargs (dict, optional): Arguments for table extraction.
        boundary_preprocessing (bool): Whether to perform figure/table boundary
            extraction. If False, processes the entire page image.

    Returns:
        list[Detection]: List of all saved detection objects for the document.
    """
    logger.info(
        f"Analyze document called for doc: {document_id}, config: {config_id}"
    )

    if figure_kwargs is None:
        figure_kwargs = {}
    if table_kwargs is None:
        table_kwargs = {}

    pdf = get_pdf_object(document_id)
    logger.info(
        f"Loaded PDF document with {len(pdf)} pages for document {document_id}"
    )  # noqa E501
    from ocr.models import OCRConfig  # Local import

    try:
        ocr_config_model_instance = OCRConfig.objects.get(pk=config_id)
        param_config_name = ocr_config_model_instance.name
        paddle_params = ocr_config_model_instance.config["paddle"]
    except OCRConfig.DoesNotExist:
        logger.warning(
            f"OCRConfig with ID {config_id} not found. Using ID as name."
        )
        param_config_name = str(config_id)

    try:
        page_render_scale = ocr_config_model_instance.config["scale"]
    except KeyError:
        logger.warning(
            f"Scale not found in OCRConfig with ID {config_id}. Using default."
        )
        page_render_scale = 4.0

    # Iterate through each page of the PDF
    for page_idx, page_obj in enumerate(pdf):
        page_number = page_idx + 1
        logger.info(
            f"[{config_id}] Processing page {page_number} for document {document_id}"  # noqa E501
        )

        page_im = page_to_image(page_obj, page_render_scale)

        # Create page in db
        try:
            page_db = _create_page_in_db(document_id, page_number)
        except Exception as e:
            logger.error(
                f"Error creating page in DB for doc {document_id}, page {page_number}: {e}",  # noqa E501
                exc_info=True,
            )
            continue

        # Extract figure and table regions from the page image
        if boundary_preprocessing:
            figure_npd, table_npd, figure_offset, table_offset = (
                figure_table_extraction(
                    page_im,
                    figure_kwargs=figure_kwargs,
                    table_kwargs=table_kwargs,
                )
            )

            logger.info("Gathering detections for figures and tables...")
            figure_dets = _extract_detections_from_image(
                figure_npd,
                # ocr,
                paddle_params,
                config_id,
                page_db.id,
            )
            table_dets = _extract_detections_from_image(
                table_npd,
                # ocr,
                paddle_params,
                config_id,
                page_db.id,
            )

            # Adjust and save detections
            _adjust_and_save_detections(
                figure_dets,
                figure_offset[0],
                figure_offset[1],
                page_render_scale,
            )

            _adjust_and_save_detections(
                table_dets,
                table_offset[0],
                table_offset[1],
                page_render_scale,
            )
        else:
            logger.info(
                "Processing entire page image without boundary extraction..."
            )
            page_dets = _extract_detections_from_image(
                page_im,
                # ocr,
                paddle_params,
                config_id,
                page_db.id,
            )

            # Adjust and save detections with no offset
            _adjust_and_save_detections(
                page_dets,
                0,  # No x offset
                0,  # No y offset
                page_render_scale,
            )

        page_obj.close()

    pdf.close()

    logger.info(f"[{param_config_name}] Completed document {document_id}. ")

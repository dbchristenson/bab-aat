import logging

import cv2 as cv
import numpy as np
from preprocess_utils import (
    _calculate_edge_thresholds,
    _calculate_min_area_threshold,
    _filter_contours_by_area_and_edge,
    _get_image_dimensions,
    _identify_primary_candidates,
    _select_smallest_contour,
)


def find_significant_inner_boundary(
    all_contours: list,
    img: np.ndarray,
    min_area_ratio: float = 0.01,
    edge_margin_ratio: float = 0.001,
    area_drop_off_ratio: float = 1.75,
) -> list:  # Returns a list containing one contour, or an empty list
    """
    Finds the most likely inner significant boundary contour in an image.
    This is designed for documents with nested rectangular borders.

    Args:
        all_contours (list): All contours found in the image.
        img (numpy.ndarray): The image (used for dimensions).
        min_area_ratio (float): Min contour area as fraction of image area.
        edge_margin_ratio (float): Border margin to identify edge artifacts.
        area_drop_off_ratio (float): Area ratio for detecting area drop-off.

    Returns:
        list: A list containing the identified boundary contour, or empty list.
    """
    logging.info("\n--- Finding significant inner boundary ---")
    if not all_contours:
        logging.warning("Warning: No contours provided.")
        return []

    try:
        h_img, w_img = _get_image_dimensions(img)
    except ValueError as e:
        logging.critical(f"Error getting image dimensions: {e}")
        return []

    logging.debug(f"Image Dimensions (HxW): {h_img} x {w_img}")

    min_area_thresh = _calculate_min_area_threshold(
        h_img, w_img, min_area_ratio
    )
    logging.debug(
        f"Min Area Threshold ({min_area_ratio*100:.2f}% of total): {min_area_thresh:.2f}"  # noqa: E501
    )

    x_min, x_max, y_min, y_max = _calculate_edge_thresholds(
        h_img, w_img, edge_margin_ratio
    )
    logging.debug(
        f"Edge Thresholds: x=[{x_min:.2f}, {x_max:.2f}], y=[{y_min:.2f}, {y_max:.2f}]"  # noqa: E501
    )

    # Initial filtering
    valid_contours_data = _filter_contours_by_area_and_edge(
        all_contours, min_area_thresh, x_min, x_max, y_min, y_max
    )
    logging.debug(
        f"Found {len(valid_contours_data)} contours after area and edge filtering."  # noqa: E501
    )

    if not valid_contours_data:
        logging.critical(
            "Warning: No valid contours remaining after initial filtering."
        )
        return []

    # Identify primary candidates based on area drop-off
    # Note: _identify_primary_candidates expects data sorted descending by area
    valid_contours_data.sort(
        key=lambda item: item["area"], reverse=True
    )  # Ensure sort order
    primary_candidates_data = _identify_primary_candidates(
        valid_contours_data, area_drop_off_ratio
    )
    logging.debug(
        f"Identified {len(primary_candidates_data)} primary candidates."
    )

    if not primary_candidates_data:
        logging.critical("Warning: No primary candidates identified.")
        return []

    # Select the smallest area contour from the primary candidates
    figure_contour_list = _select_smallest_contour(primary_candidates_data)

    if figure_contour_list:
        logging.debug(
            f"Selected inner boundary contour with area: {cv.contourArea(figure_contour_list[0]):.2f}"  # noqa: E501
        )
    else:
        logging.warning(
            "Warning: Could not select a final inner boundary contour from candidates."  # noqa: E501
        )

    return figure_contour_list

import math  # For checking non-finite numbers

import cv2 as cv
import numpy as np

# --- Helper Functions ---


def _get_image_dimensions(img: np.ndarray) -> tuple[int, int]:
    """Gets the height and width of the image."""
    if img.ndim == 2:  # Grayscale
        h_img, w_img = img.shape
    elif img.ndim == 3:  # Color
        h_img, w_img, _ = img.shape
    else:
        raise ValueError(
            f"Unsupported image dimensions: {img.ndim}. Expected 2 or 3."
        )
    return h_img, w_img


def _calculate_min_area_threshold(
    img_height: int, img_width: int, min_area_ratio: float
) -> float:
    """Calculates the minimum area threshold for a contour."""
    total_image_area = img_height * img_width
    return total_image_area * min_area_ratio


def _calculate_edge_thresholds(
    img_height: int, img_width: int, edge_margin_ratio: float
) -> tuple[float, float, float, float]:
    """Calculates the pixel thresholds for detecting edge artifacts."""
    x_thresh_min = edge_margin_ratio * img_width
    x_thresh_max = img_width - x_thresh_min
    y_thresh_min = edge_margin_ratio * img_height
    y_thresh_max = img_height - y_thresh_min
    return x_thresh_min, x_thresh_max, y_thresh_min, y_thresh_max


def _filter_contours_by_area_and_edge(
    contours: list,
    min_area_threshold: float,
    x_thresh_min: float,
    x_thresh_max: float,
    y_thresh_min: float,
    y_thresh_max: float,
) -> list:
    """
    Filters contours based on minimum area and proximity to image edges.

    Returns:
        list: A list of dictionaries, each {'contour': contour, 'area': area}.
    """
    filtered_contours_data = []
    for contour in contours:
        area = cv.contourArea(contour)
        if area < min_area_threshold:
            continue

        x, y, w, h = cv.boundingRect(contour)
        x_max_bbox = x + w
        y_max_bbox = y + h

        is_edge_artifact = (
            x < x_thresh_min
            or y < y_thresh_min
            or x_max_bbox > x_thresh_max
            or y_max_bbox > y_thresh_max
        )

        if not is_edge_artifact:
            filtered_contours_data.append({"contour": contour, "area": area})
    return filtered_contours_data


def _identify_primary_candidates(
    valid_contours_data: list,  # List of {'contour': contour, 'area': area}
    area_drop_off_ratio: float,
) -> list:
    """
    Identifies a group of primary contours by looking for a significant
    drop-off in area among the largest remaining contours.

    Args:
        valid_contours_data (list): Contours sorted by area, descending.
        area_drop_off_ratio (float): Area ratio threshold.

    Returns:
        list: List of primary candidate contours (dictionaries with 'contour'
              and 'area').
    """
    if not valid_contours_data:
        return []

    primary_candidates = []
    # Sort by area descending, if not already (defensive)
    valid_contours_data.sort(key=lambda item: item["area"], reverse=True)

    if len(valid_contours_data) == 1:
        return valid_contours_data  # Only one candidate

    primary_candidates.append(
        valid_contours_data[0]
    )  # Add the largest unconditionally

    for i in range(len(valid_contours_data) - 1):
        current_area = valid_contours_data[i]["area"]
        next_area = valid_contours_data[i + 1]["area"]

        if next_area <= 1e-6:  # Avoid division by zero or very small numbers
            break

        ratio = current_area / next_area
        if not math.isfinite(ratio) or ratio >= area_drop_off_ratio:
            break  # Significant drop or invalid ratio
        else:
            primary_candidates.append(valid_contours_data[i + 1])

    return primary_candidates


def _select_smallest_contour(
    primary_candidates: list,
) -> list:  # Returns list with 0 or 1 contour
    """
    Selects the contour with the smallest area from the primary candidates.

    Args:
        primary_candidates (list): List of {'contour': contour, 'area': area}.

    Returns:
        list: A list containing the smallest contour, or an empty list.
    """
    if not primary_candidates:
        return []

    # Sort by area ascending to find the smallest
    primary_candidates.sort(key=lambda item: item["area"])
    return [primary_candidates[0]["contour"]]

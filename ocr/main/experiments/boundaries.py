import logging
import math  # For checking non-finite numbers

import cv2 as cv
import matplotlib.pyplot as plt
import numpy as np

gray_cmap = plt.get_cmap("gray")

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


# --- Main Function ---


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


def _find_contours(
    img,
    min_thresh=127,
    max_thresh=255,
    mode=cv.RETR_TREE,
    method=cv.CHAIN_APPROX_SIMPLE,
):
    """
    Takes a MatLike object and returns contours. This function handles the
    binarization of the image as well as the contour finding.
    """
    ret, thresh = cv.threshold(img, min_thresh, max_thresh, 0)
    all_contours, hierarchy = cv.findContours(thresh, mode, method)

    return all_contours


def _draw_bbox_on_image(img, bbox, color=(0, 255, 0), thickness=2):
    """
    Draws a bounding box on the image and displays it.
    """
    x, y, w, h = bbox
    cv.rectangle(img, (x, y), (x + w, y + h), color, thickness)

    # Display the image with the bounding box
    plt.imshow(img, cmap=gray_cmap)
    plt.axis("off")
    plt.show()

    return img


def _figure_extraction(img, **kwargs):
    """
    Takes a MatLike object and returns the bbox of the figure translated to
    the original image coordinate system.

    Args:
        img (MatLike): The image to process.
        **kwargs: Additional arguments for contour finding.
            - min_area_ratio (float): Minimum area ratio for contour filter.
            - edge_margin_ratio (float): Edge margin ratio for contour filter.
            - area_drop_off_ratio (float): Drop-off ratio for contour filter.
            - show_bbox (bool): Bool to display the bounding box on the image.

    Returns:
        tuple: The bounding box of the figure in the format (x, y, w, h).
    """
    contours = _find_contours(img)

    if not contours:
        logging.warning(
            "No contours found in the image. Using fallback of entire image."
        )
        contours = [
            np.array(
                [
                    [0, 0],
                    [img.shape[1], 0],
                    [img.shape[1], img.shape[0]],
                    [0, img.shape[0]],
                ]
            )
        ]

    contour_candidates = find_significant_inner_boundary(
        all_contours=contours,
        img=img,
        min_area_ratio=kwargs.get("min_area_ratio", 0.01),  # 1% min area
        edge_margin_ratio=kwargs.get(
            "edge_margin_ratio", 0.005
        ),  # 0.1% edge margin
        area_drop_off_ratio=kwargs.get(
            "area_drop_off_ratio", 1.75
        ),  # Drop-off if area ratio > 1.75
    )

    if not contour_candidates:
        logging.warning("No significant inner boundary found. Using fallback.")
        sorted_contours = sorted(contours, key=cv.contourArea, reverse=True)
        best_candidate = sorted_contours[0]
    else:
        best_candidate = contour_candidates[0]

    figure_bbox = cv.boundingRect(best_candidate)

    if kwargs.get("show_bbox", False):
        _draw_bbox_on_image(img, figure_bbox)

    return figure_bbox


def _table_extraction(img, figure_bbox, **kwargs):
    """
    Takes a MatLike object and returns the bbox of the table translated to
    the original image coordinate system.

    Args:
        img (MatLike): The image to process.
        figure_bbox (tuple | list): The bounding box of the figure.
        **kwargs: Additional arguments for contour finding.
            - show_bbox (bool): Whether to show the bounding box on the image.

    Returns:
        tuple: The bounding box of the table in the format (x, y, w, h).
    """
    # Crop original image everything to the right of the figure bbox
    # and trim the top and bottom of the image to the figure bbox
    fx, fy, fw, fh = figure_bbox

    print(img.shape)
    ih, iw = img.shape

    table_bbox = fx + fw, fy, iw, fh
    print(table_bbox)

    if kwargs.get("show_bbox", False):
        _draw_bbox_on_image(img, table_bbox)

    return table_bbox


def figure_table_extraction(img_path: str, **kwargs):
    """
    Takes an image path and returns the cropped figure and table images.

    Args:
        img_path (str): Path to the image file.
    """
    # load image
    img = cv.imread(img_path, cv.IMREAD_GRAYSCALE)

    # figure extraction
    try:
        figure_kwargs = kwargs.get("figure_kwargs", {})
        figure_bbox = _figure_extraction(img, kwargs=figure_kwargs)
    except Exception as e:
        print(f"Error during figure extraction: {e}")
        return None, None

    # table extraction
    try:
        table_kwargs = kwargs.get("table_kwargs", {})
        table_bbox = _table_extraction(img, figure_bbox, kwargs=table_kwargs)
    except Exception as e:
        print(f"Error during table extraction: {e}")
        return None, None

    # crop image
    fx, fy, fw, fh = figure_bbox
    tx, ty, tw, th = table_bbox

    figure_crop = img[fy : fy + fh, fx : fx + fw]  # noqa: E203
    table_crop = img[ty : ty + th, tx : tx + tw]  # noqa: E203

    return figure_crop, table_crop

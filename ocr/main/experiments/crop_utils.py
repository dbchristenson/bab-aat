import copy
import math

import cv2
import numpy as np

# flake8: noqa


def find_boundary_lines(
    img,
    blurred,
    canny_thresh1=50,
    canny_thresh2=150,
    hough_thresh=50,
    min_line_length=100,
    max_line_gap=20,
    angle_tolerance=2.0,
):
    """
    Detects horizontal and vertical lines in an image and attempts to identify
    the innermost border lines defining the main figure and table areas.

    Args:
        img (np.ndarray): Input image as a NumPy array.
        blurred (np.ndarray): Blurred version of the input image.
        canny_thresh1 (int): Lower threshold for Canny edge detection.
        canny_thresh2 (int): Higher threshold for Canny edge detection.
        hough_thresh (int): Accumulator threshold parameter for HoughLinesP.
                            Only lines receiving more votes than this are returned.
        min_line_length (int): Minimum line length. Line segments shorter than this are rejected.
        max_line_gap (int): Maximum allowed gap between points on the same line to link them.
        angle_tolerance (float): Tolerance in degrees to consider a line horizontal or vertical.

    Returns:
        tuple: A tuple containing (image_height, image_width, V_lines, H_lines)
               where V_lines and H_lines are lists of detected vertical and horizontal lines,
               each line represented as ((x1, y1), (x2, y2)).
               Returns (None, None, None, None) if the image cannot be read.
        None: If image loading fails.
    """
    if img is None:
        return None

    height, width = img.shape[:2]

    # Use Canny edge detector
    edges = cv2.Canny(blurred, canny_thresh1, canny_thresh2)

    # Use Probabilistic Hough Line Transform
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        hough_thresh,
        minLineLength=min_line_length,
        maxLineGap=max_line_gap,
    )

    V_lines = []
    H_lines = []

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # Calculate angle
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))

            # Filter for nearly vertical lines
            if (
                abs(angle - 90) < angle_tolerance
                or abs(angle + 90) < angle_tolerance
            ):
                # Ensure it's reasonably long vertically
                if (
                    abs(y1 - y2) > min_line_length * 0.5
                ):  # Adjust multiplier as needed
                    V_lines.append(((x1, y1), (x2, y2)))

            # Filter for nearly horizontal lines
            elif (
                abs(angle - 0) < angle_tolerance
                or abs(angle - 180) < angle_tolerance
                or abs(angle + 180) < angle_tolerance
            ):
                # Ensure it's reasonably long horizontally
                if (
                    abs(x1 - x2) > min_line_length * 0.5
                ):  # Adjust multiplier as needed
                    H_lines.append(((x1, y1), (x2, y2)))

    print(f"Detected {len(V_lines)} potential vertical lines.")
    print(f"Detected {len(H_lines)} potential horizontal lines.")

    return height, width, V_lines, H_lines


import math

import cv2
import numpy as np


def get_figure_and_table_boundaries(
    height,
    width,
    V_lines,
    H_lines,
    border_margin_ratio=0.15,
    max_crawl_ratio=0.30,
    edge_buffer_px=10,  # New parameter: Ignore lines within this many pixels of the absolute edge
    divider_search_ratio_start=0.6,
):
    """
    Analyzes detected lines to find boundaries, with robust fallback search
    and buffering to ignore lines too close to the absolute image edge.

    Args:
        height (int): Image height.
        width (int): Image width.
        V_lines (list): List of vertical lines (((x1, y1), (x2, y2)), ...).
        H_lines (list): List of horizontal lines (((x1, y1), (x2, y2)), ...).
        border_margin_ratio (float): Initial ratio from edge to search for boundaries.
        max_crawl_ratio (float): If initial search fails, max ratio from edge
                                 to expand search for boundaries.
        edge_buffer_px (int): Minimum pixels lines must be away from the image edge
                              to be considered valid boundary candidates.
        divider_search_ratio_start (float): Ratio of width to start searching for divider.

    Returns:
        dict: A dictionary containing coordinates:
              {'y_top': y, 'y_bottom': y, 'x_left': x, 'x_divider': x, 'x_right': x}
              Returns None if essential boundaries cannot be determined.
    """
    if not V_lines or not H_lines:
        print("Error: Not enough lines detected to determine boundaries.")
        return None

    # --- Define Search Areas ---
    initial_margin_x = int(width * border_margin_ratio)
    initial_margin_y = int(height * border_margin_ratio)
    max_crawl_dist_x = int(width * max_crawl_ratio)
    max_crawl_dist_y = int(height * max_crawl_ratio)

    # Ensure buffer isn't excessively large
    safe_buffer_x = max(0, min(edge_buffer_px, width // 10))
    safe_buffer_y = max(0, min(edge_buffer_px, height // 10))

    boundaries = {}
    print(f"Edge buffers set to: x={safe_buffer_x}px, y={safe_buffer_y}px")

    # --- Find Innermost Top Horizontal Line ---
    # 1. Try initial margin, ignoring lines too close to the top edge
    top_candidates = [
        max(l[0][1], l[1][1])
        for l in H_lines
        if safe_buffer_y < max(l[0][1], l[1][1]) < initial_margin_y
    ]
    if top_candidates:
        boundaries["y_top"] = int(max(top_candidates))
    else:
        print(
            f"Warning: No top line in initial margin ({initial_margin_y}px, buffer {safe_buffer_y}px). Expanding search to {max_crawl_dist_y}px."
        )
        # 2. Try expanded search area, ignoring lines too close to the top edge
        top_candidates_expanded = [
            max(l[0][1], l[1][1])
            for l in H_lines
            if safe_buffer_y < max(l[0][1], l[1][1]) < max_crawl_dist_y
        ]
        if top_candidates_expanded:
            boundaries["y_top"] = int(max(top_candidates_expanded))
        else:
            print(
                "Warning: No top line found even in expanded search (buffer ignored). Using fallback."
            )
            # 3. Fallback: Use the highest horizontal line found overall (that's not the edge buffer) or a fixed small offset
            all_h_y_coords = sorted(
                [
                    (l[0][1] + l[1][1]) / 2
                    for l in H_lines
                    if (l[0][1] + l[1][1]) / 2 > safe_buffer_y
                ]
            )
            boundaries["y_top"] = (
                int(all_h_y_coords[0]) if all_h_y_coords else safe_buffer_y + 1
            )  # Default fallback

    # --- Find Innermost Bottom Horizontal Line ---
    # 1. Try initial margin, ignoring lines too close to the bottom edge
    bottom_candidates = [
        min(l[0][1], l[1][1])
        for l in H_lines
        if height - initial_margin_y
        < min(l[0][1], l[1][1])
        < height - safe_buffer_y
    ]
    if bottom_candidates:
        boundaries["y_bottom"] = int(min(bottom_candidates))
    else:
        print(
            f"Warning: No bottom line in initial margin ({initial_margin_y}px, buffer {safe_buffer_y}px). Expanding search up to {max_crawl_dist_y}px from bottom."
        )
        # 2. Try expanded search area, ignoring lines too close to the bottom edge
        bottom_candidates_expanded = [
            min(l[0][1], l[1][1])
            for l in H_lines
            if height - max_crawl_dist_y
            < min(l[0][1], l[1][1])
            < height - safe_buffer_y
        ]
        if bottom_candidates_expanded:
            boundaries["y_bottom"] = int(min(bottom_candidates_expanded))
        else:
            print(
                "Warning: No bottom line found even in expanded search (buffer ignored). Using fallback."
            )
            # 3. Fallback: Use the lowest horizontal line found overall (that's not the edge buffer) or a fixed small offset
            all_h_y_coords = sorted(
                [
                    (l[0][1] + l[1][1]) / 2
                    for l in H_lines
                    if (l[0][1] + l[1][1]) / 2 < height - safe_buffer_y
                ],
                reverse=True,
            )
            boundaries["y_bottom"] = (
                int(all_h_y_coords[0])
                if all_h_y_coords
                else height - safe_buffer_y - 1
            )  # Default fallback

    # --- Find Innermost Left Vertical Line ---
    # 1. Try initial margin, ignoring lines too close to the left edge
    left_candidates = [
        max(l[0][0], l[1][0])
        for l in V_lines
        if safe_buffer_x < max(l[0][0], l[1][0]) < initial_margin_x
    ]
    if left_candidates:
        boundaries["x_left"] = int(max(left_candidates))
    else:
        print(
            f"Warning: No left line in initial margin ({initial_margin_x}px, buffer {safe_buffer_x}px). Expanding search to {max_crawl_dist_x}px."
        )
        # 2. Try expanded search area, ignoring lines too close to the left edge
        left_candidates_expanded = [
            max(l[0][0], l[1][0])
            for l in V_lines
            if safe_buffer_x < max(l[0][0], l[1][0]) < max_crawl_dist_x
        ]
        if left_candidates_expanded:
            boundaries["x_left"] = int(max(left_candidates_expanded))
        else:
            print(
                "Warning: No left line found even in expanded search (buffer ignored). Using fallback."
            )
            # 3. Fallback: Use the leftmost vertical line found overall (that's not the edge buffer) or a fixed small offset
            all_v_x_coords = sorted(
                [
                    (l[0][0] + l[1][0]) / 2
                    for l in V_lines
                    if (l[0][0] + l[1][0]) / 2 > safe_buffer_x
                ]
            )
            boundaries["x_left"] = (
                int(all_v_x_coords[0]) if all_v_x_coords else safe_buffer_x + 1
            )  # Default fallback

    # --- Find Innermost Right Vertical Line (for Table) ---
    # 1. Try initial margin, ignoring lines too close to the right edge
    right_candidates = [
        min(l[0][0], l[1][0])
        for l in V_lines
        if width - initial_margin_x
        < min(l[0][0], l[1][0])
        < width - safe_buffer_x
    ]
    if right_candidates:
        boundaries["x_right"] = int(min(right_candidates))
    else:
        print(
            f"Warning: No right line in initial margin ({initial_margin_x}px, buffer {safe_buffer_x}px). Expanding search up to {max_crawl_dist_x}px from right."
        )
        # 2. Try expanded search area, ignoring lines too close to the right edge
        right_candidates_expanded = [
            min(l[0][0], l[1][0])
            for l in V_lines
            if width - max_crawl_dist_x
            < min(l[0][0], l[1][0])
            < width - safe_buffer_x
        ]
        if right_candidates_expanded:
            boundaries["x_right"] = int(min(right_candidates_expanded))
        else:
            print(
                "Warning: No right line found even in expanded search (buffer ignored). Using fallback."
            )
            # 3. Fallback: Use the rightmost vertical line found overall (that's not the edge buffer) or a fixed small offset
            all_v_x_coords = sorted(
                [
                    (l[0][0] + l[1][0]) / 2
                    for l in V_lines
                    if (l[0][0] + l[1][0]) / 2 < width - safe_buffer_x
                ],
                reverse=True,
            )
            boundaries["x_right"] = (
                int(all_v_x_coords[0])
                if all_v_x_coords
                else width - safe_buffer_x - 1
            )  # Default fallback

    # --- Find Divider Vertical Line (Logic remains similar, but uses determined x_left/x_right) ---
    # Check if essential boundaries were found before proceeding
    if "x_left" not in boundaries or "x_right" not in boundaries:
        print(
            "Error: Could not determine left or right boundary, cannot find divider."
        )
        return None

    divider_search_start_x = int(width * divider_search_ratio_start)
    # Ensure divider search starts after the determined x_left and ends before determined x_right
    actual_divider_search_start = max(
        divider_search_start_x, boundaries["x_left"] + safe_buffer_x
    )  # Start after x_left + buffer
    actual_divider_search_end = (
        boundaries["x_right"] - safe_buffer_x
    )  # End before x_right - buffer

    divider_candidates = []
    min_divider_height = height * 0.5  # Require line to be significantly long
    for l in V_lines:
        x_avg = (l[0][0] + l[1][0]) / 2
        line_len = abs(l[0][1] - l[1][1])
        # Check if the line is within the refined divider region and long enough
        if (
            actual_divider_search_start < x_avg < actual_divider_search_end
            and line_len > min_divider_height
        ):
            # Ensure divider line itself is not too close to top/bottom edges either
            y_min_line = min(l[0][1], l[1][1])
            y_max_line = max(l[0][1], l[1][1])
            if (
                y_min_line > safe_buffer_y
                and y_max_line < height - safe_buffer_y
            ):
                divider_candidates.append(x_avg)

    if not divider_candidates:
        print(
            "Warning: Could not find a clear divider line candidate. Using heuristic estimate between determined left/right."
        )
        # Fallback: Estimate based on determined x_left and x_right
        boundaries["x_divider"] = int(
            boundaries["x_left"]
            + (boundaries["x_right"] - boundaries["x_left"]) * 0.8
        )  # Default fallback ratio
    else:
        # Choose the leftmost candidate in the potential divider area seems reasonable
        boundaries["x_divider"] = int(min(divider_candidates))

    # --- Final Validation ---
    # Check if the derived boundaries make logical sense
    y_top = boundaries.get("y_top", -1)
    y_bottom = boundaries.get("y_bottom", -1)
    x_left = boundaries.get("x_left", -1)
    x_divider = boundaries.get("x_divider", -1)
    x_right = boundaries.get("x_right", -1)

    if not (
        safe_buffer_y <= y_top < y_bottom <= height - safe_buffer_y
        and safe_buffer_x
        <= x_left
        < x_divider
        < x_right
        <= width - safe_buffer_x
    ):
        print(
            f"Error: Calculated boundaries are illogical, out of bounds, or too close to edge after buffering."
        )
        print(
            f"Values: y_top={y_top}, y_bottom={y_bottom}, x_left={x_left}, x_divider={x_divider}, x_right={x_right}"
        )
        return None

    print(f"Calculated Boundaries (Robust, Buffered): {boundaries}")
    return boundaries


def extract_regions(img, boundaries, padding=5):
    """
    Extracts the figure and table regions from the image based on calculated boundaries.

    Args:
        img (np.ndarray): Input image as a NumPy array.
        boundaries (dict): Dictionary containing the boundary coordinates.
        padding (int): Pixels to add/subtract from boundaries for cleaner cropping.

    Returns:
        tuple: (figure_image, table_image, figure_offset, table_offset)
               Returns (None*4) if input is invalid or cropping fails.
    """
    if boundaries is None:
        print("Error: No boundaries provided for extraction.")
        return None, None, None, None

    if img is None:
        return None, None, None, None

    h, w = img.shape[:2]

    # Apply padding and ensure coordinates are within image bounds
    # Calculate crop coordinates with padding and bounds checking
    y_top_crop = max(0, boundaries["y_top"] + padding)
    y_bottom_crop = min(h, boundaries["y_bottom"] - padding)
    x_left_crop = max(0, boundaries["x_left"] + padding)
    x_divider_fig_crop = min(
        w, boundaries["x_divider"] - padding
    )  # Right edge for figure
    x_divider_tab_crop = max(
        0, boundaries["x_divider"] + padding
    )  # Left edge for table
    x_right_crop = min(w, boundaries["x_right"] - padding)

    # Check for invalid crop dimensions immediately after calculation
    valid_figure_crop = (y_top_crop < y_bottom_crop) and (
        x_left_crop < x_divider_fig_crop
    )
    valid_table_crop = (y_top_crop < y_bottom_crop) and (
        x_divider_tab_crop < x_right_crop
    )

    if not valid_figure_crop or not valid_table_crop:
        print(
            f"Warning: Invalid crop dimensions calculated with padding. Trying without."
        )
        # Attempt without padding as a fallback
        y_top_crop = boundaries["y_top"]
        y_bottom_crop = boundaries["y_bottom"]
        x_left_crop = boundaries["x_left"]
        x_divider_fig_crop = boundaries["x_divider"]
        x_divider_tab_crop = boundaries["x_divider"]
        x_right_crop = boundaries["x_right"]

        valid_figure_crop = (y_top_crop < y_bottom_crop) and (
            x_left_crop < x_divider_fig_crop
        )
        valid_table_crop = (y_top_crop < y_bottom_crop) and (
            x_divider_tab_crop < x_right_crop
        )

        if not valid_figure_crop or not valid_table_crop:
            print(
                "Error: Invalid crop dimensions even without padding. Cannot extract."
            )
            return None, None, None, None  # Give up if still invalid

    # Define the offsets (top-left corner of the crop in original image)
    # These are the start indices of the slices
    figure_offset = (x_left_crop, y_top_crop)
    table_offset = (x_divider_tab_crop, y_top_crop)

    # Crop the regions using the calculated coordinates
    figure_image = img[y_top_crop:y_bottom_crop, x_left_crop:x_divider_fig_crop]
    table_image = img[y_top_crop:y_bottom_crop, x_divider_tab_crop:x_right_crop]

    print(
        f"Figure extracted: shape={figure_image.shape} at offset {figure_offset}"
    )
    print(
        f"Table extracted: shape={table_image.shape} at offset {table_offset}"
    )

    return figure_image, table_image, figure_offset, table_offset


def translate_ocr_coordinates(
    figure_ocr_results, table_ocr_results, figure_offset, table_offset
):
    """
    Translates bounding box coordinates from cropped image space to original image space.

    Args:
        figure_ocr_results (list): List of OCR result dicts for the figure crop.
                                   Each dict should have a 'bbox' key like [x, y, w, h].
        table_ocr_results (list): List of OCR result dicts for the table crop.
                                  Each dict should have a 'bbox' key like [x, y, w, h].
        figure_offset (tuple): (x, y) offset of the figure crop's top-left corner
                               in the original image.
        table_offset (tuple): (x, y) offset of the table crop's top-left corner
                              in the original image.

    Returns:
        list: A combined list of OCR result dicts with 'bbox' coordinates
              translated to the original image's coordinate system.
              Returns an empty list if inputs are invalid.
    """
    if figure_offset is None or table_offset is None:
        print("Error: Invalid offsets provided for coordinate translation.")
        return []

    combined_results = []
    figure_offset_x, figure_offset_y = figure_offset
    table_offset_x, table_offset_y = (
        table_offset  # y offset is usually the same
    )

    # Process figure results
    if figure_ocr_results:
        for result in figure_ocr_results:
            # Make a deep copy to avoid modifying the original list/dictionaries
            new_result = copy.deepcopy(result)
            try:
                relative_bbox = new_result["bbox"]
                x_rel, y_rel, w, h = relative_bbox

                # Translate coordinates by adding the offset
                x_abs = x_rel + figure_offset_x
                y_abs = y_rel + figure_offset_y

                # Update the bbox in the new result dictionary
                new_result["bbox"] = [x_abs, y_abs, w, h]
                new_result["source_crop"] = "figure"  # Add info about origin
                combined_results.append(new_result)

            except (KeyError, IndexError, TypeError) as e:
                print(
                    f"Warning: Skipping result due to invalid format: {result}. Error: {e}"
                )
                continue

    # Process table results
    if table_ocr_results:
        for result in table_ocr_results:
            new_result = copy.deepcopy(result)
            try:
                relative_bbox = new_result["bbox"]
                x_rel, y_rel, w, h = relative_bbox

                # Translate coordinates by adding the offset
                x_abs = x_rel + table_offset_x
                y_abs = y_rel + table_offset_y  # Note: uses table_offset_x

                # Update the bbox in the new result dictionary
                new_result["bbox"] = [x_abs, y_abs, w, h]
                new_result["source_crop"] = "table"  # Add info about origin
                combined_results.append(new_result)

            except (KeyError, IndexError, TypeError) as e:
                print(
                    f"Warning: Skipping result due to invalid format: {result}. Error: {e}"
                )
                continue

    print(f"Translated coordinates for {len(combined_results)} OCR results.")
    return combined_results


def calculate_black_pixel_ratio(image_slice):
    """Calculates the ratio of black pixels (value 0) in a given slice."""
    if image_slice is None or image_slice.size == 0:
        return 0.0
    # Ensure the image is 2D (grayscale/binary)
    if len(image_slice.shape) > 2:
        # Convert to grayscale if needed, assuming BGR format
        image_slice = cv2.cvtColor(image_slice, cv2.COLOR_BGR2GRAY)

    # Threshold if not already binary (adjust threshold value if needed)
    # Assuming black pixels are close to 0 and white pixels are close to 255
    # Using Otsu's method can be good for adaptive thresholding
    _, binary_slice = cv2.threshold(
        image_slice, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    # Or a fixed threshold if contrast is reliable:
    # _, binary_slice = cv2.threshold(image_slice, 128, 255, cv2.THRESH_BINARY_INV)

    black_pixels = np.count_nonzero(
        binary_slice == 255
    )  # Pixels are 255 after THRESH_BINARY_INV
    total_pixels = binary_slice.size
    ratio = black_pixels / total_pixels if total_pixels > 0 else 0.0
    return ratio


def find_edge_buffers(
    img_binary, scan_depth_px=50, artifact_threshold_alpha=0.8, slice_step_px=2
):
    """
    Detects solid artifact borders and determines the required buffer size for each side.

    Args:
        img_binary (np.array): Input image, preprocessed (grayscale/binary).
                                Assumes black is 0, white is 255.
        scan_depth_px (int): How many pixels deep from the edge to check initially.
        artifact_threshold_alpha (float): Ratio of black pixels to classify as artifact.
        slice_step_px (int): Step size for inward slicing when searching artifact end.

    Returns:
        dict: {'top': buffer_px, 'bottom': buffer_px, 'left': buffer_px, 'right': buffer_px}
    """
    height, width = img_binary.shape[:2]
    buffers = {"top": 0, "bottom": 0, "left": 0, "right": 0}

    # --- Top Buffer ---
    initial_slice_top = img_binary[0:scan_depth_px, :]
    if (
        calculate_black_pixel_ratio(initial_slice_top)
        > artifact_threshold_alpha
    ):
        print("Artifact detected: Top")
        for y in range(
            slice_step_px, scan_depth_px * 2, slice_step_px
        ):  # Search deeper if needed
            current_slice = img_binary[y : y + slice_step_px, :]
            if (
                calculate_black_pixel_ratio(current_slice)
                < artifact_threshold_alpha
            ):
                buffers["top"] = y
                print(f"  Top buffer set to: {y}px")
                break
        else:  # If loop finishes without breaking
            print(
                f"  Warning: Top artifact persists beyond search depth. Using default buffer: {scan_depth_px}"
            )
            buffers["top"] = scan_depth_px  # Fallback if artifact is very thick

    # --- Bottom Buffer ---
    initial_slice_bottom = img_binary[height - scan_depth_px : height, :]
    if (
        calculate_black_pixel_ratio(initial_slice_bottom)
        > artifact_threshold_alpha
    ):
        print("Artifact detected: Bottom")
        for y in range(slice_step_px, scan_depth_px * 2, slice_step_px):
            current_slice = img_binary[
                height - y - slice_step_px : height - y, :
            ]
            if (
                calculate_black_pixel_ratio(current_slice)
                < artifact_threshold_alpha
            ):
                buffers["bottom"] = y
                print(f"  Bottom buffer set to: {y}px")
                break
        else:
            print(
                f"  Warning: Bottom artifact persists beyond search depth. Using default buffer: {scan_depth_px}"
            )
            buffers["bottom"] = scan_depth_px

    # --- Left Buffer ---
    initial_slice_left = img_binary[:, 0:scan_depth_px]
    if (
        calculate_black_pixel_ratio(initial_slice_left)
        > artifact_threshold_alpha
    ):
        print("Artifact detected: Left")
        for x in range(slice_step_px, scan_depth_px * 2, slice_step_px):
            current_slice = img_binary[:, x : x + slice_step_px]
            if (
                calculate_black_pixel_ratio(current_slice)
                < artifact_threshold_alpha
            ):
                buffers["left"] = x
                print(f"  Left buffer set to: {x}px")
                break
        else:
            print(
                f"  Warning: Left artifact persists beyond search depth. Using default buffer: {scan_depth_px}"
            )
            buffers["left"] = scan_depth_px

    # --- Right Buffer ---
    initial_slice_right = img_binary[:, width - scan_depth_px : width]
    if (
        calculate_black_pixel_ratio(initial_slice_right)
        > artifact_threshold_alpha
    ):
        print("Artifact detected: Right")
        for x in range(slice_step_px, scan_depth_px * 2, slice_step_px):
            current_slice = img_binary[:, width - x - slice_step_px : width - x]
            if (
                calculate_black_pixel_ratio(current_slice)
                < artifact_threshold_alpha
            ):
                buffers["right"] = x
                print(f"  Right buffer set to: {x}px")
                break
        else:
            print(
                f"  Warning: Right artifact persists beyond search depth. Using default buffer: {scan_depth_px}"
            )
            buffers["right"] = scan_depth_px

    return buffers


def find_outer_border_edges(
    img_binary,
    buffers,
    border_start_threshold_alpha=0.05,
    slice_step_px=2,
    max_whitespace_ratio=0.3,
):
    """
    Finds the start of the actual document border after skipping buffer and whitespace.

    Args:
        img_binary (np.array): Input binary image.
        buffers (dict): Dictionary of buffer pixels for each side from find_edge_buffers.
        border_start_threshold_alpha (float): Black pixel ratio to detect border start.
        slice_step_px (int): Step size for inward slicing.
        max_whitespace_ratio (float): Max distance (as ratio of dim) to search for border.

    Returns:
        dict: {'top': y, 'bottom': y, 'left': x, 'right': x} coordinates of outer border.
              Returns None if a border cannot be reliably found.
    """
    height, width = img_binary.shape[:2]
    outer_edges = {}
    max_search_y = int(height * max_whitespace_ratio)
    max_search_x = int(width * max_whitespace_ratio)

    # --- Top Outer Edge ---
    start_y = buffers["top"]
    found_top = False
    for y in range(
        start_y, min(start_y + max_search_y, height // 2), slice_step_px
    ):
        current_slice = img_binary[
            y : y + slice_step_px, buffers["left"] : width - buffers["right"]
        ]  # Search within side buffers
        if (
            calculate_black_pixel_ratio(current_slice)
            > border_start_threshold_alpha
        ):
            outer_edges["top"] = y
            print(f"Outer border found - Top: {y}px")
            found_top = True
            break
    if not found_top:
        print("Error: Could not find top outer border within search limit.")
        return None

    # --- Bottom Outer Edge ---
    start_y = buffers["bottom"]
    found_bottom = False
    for y in range(
        start_y, min(start_y + max_search_y, height // 2), slice_step_px
    ):
        abs_y = height - 1 - y
        current_slice = img_binary[
            abs_y - slice_step_px : abs_y,
            buffers["left"] : width - buffers["right"],
        ]
        if (
            calculate_black_pixel_ratio(current_slice)
            > border_start_threshold_alpha
        ):
            outer_edges["bottom"] = abs_y  # Store the absolute coordinate
            print(f"Outer border found - Bottom: {abs_y}px")
            found_bottom = True
            break
    if not found_bottom:
        print("Error: Could not find bottom outer border within search limit.")
        return None

    # --- Left Outer Edge ---
    start_x = buffers["left"]
    found_left = False
    for x in range(
        start_x, min(start_x + max_search_x, width // 2), slice_step_px
    ):
        current_slice = img_binary[
            outer_edges["top"] : outer_edges["bottom"], x : x + slice_step_px
        ]  # Search within top/bottom edges
        if (
            calculate_black_pixel_ratio(current_slice)
            > border_start_threshold_alpha
        ):
            outer_edges["left"] = x
            print(f"Outer border found - Left: {x}px")
            found_left = True
            break
    if not found_left:
        print("Error: Could not find left outer border within search limit.")
        return None

    # --- Right Outer Edge ---
    start_x = buffers["right"]
    found_right = False
    for x in range(
        start_x, min(start_x + max_search_x, width // 2), slice_step_px
    ):
        abs_x = width - 1 - x
        current_slice = img_binary[
            outer_edges["top"] : outer_edges["bottom"],
            abs_x - slice_step_px : abs_x,
        ]
        if (
            calculate_black_pixel_ratio(current_slice)
            > border_start_threshold_alpha
        ):
            outer_edges["right"] = abs_x  # Store the absolute coordinate
            print(f"Outer border found - Right: {abs_x}px")
            found_right = True
            break
    if not found_right:
        print("Error: Could not find right outer border within search limit.")
        return None

    # Basic validation
    if not (
        outer_edges["top"] < outer_edges["bottom"]
        and outer_edges["left"] < outer_edges["right"]
    ):
        print(
            "Error: Outer border edge calculations resulted in invalid dimensions."
        )
        return None

    return outer_edges


def find_inner_border_edges(
    outer_edges,
    H_lines,
    V_lines,
    expected_border_thickness_px=150,
    search_buffer_px=50,
):
    """
    Finds the innermost border lines by searching within a band defined by
    the outer edges and expected thickness.

    Args:
        outer_edges (dict): Coordinates of the outer border edges.
        H_lines (list): List of detected horizontal lines (((x1, y1), (x2, y2)), ...).
        V_lines (list): List of detected vertical lines (((x1, y1), (x2, y2)), ...).
        expected_border_thickness_px (int): Estimated thickness of the border area.
        search_buffer_px (int): Additional buffer for the search band to handle variations.

    Returns:
        dict: {'top': y, 'bottom': y, 'left': x, 'right': x} coordinates of inner border.
              Returns None if essential borders cannot be found.
    """
    if outer_edges is None:
        return None
    inner_edges = {}
    search_band = expected_border_thickness_px + search_buffer_px

    # --- Inner Top Edge ---
    search_min_y = outer_edges["top"]
    search_max_y = outer_edges["top"] + search_band
    top_candidates = [
        max(l[0][1], l[1][1])
        for l in H_lines
        if search_min_y < (l[0][1] + l[1][1]) / 2 < search_max_y
    ]  # Check midpoint is in band
    if top_candidates:
        inner_edges["top"] = int(max(top_candidates))  # Innermost is max Y
        print(
            f"Inner border found - Top: {inner_edges['top']}px (search band {search_min_y}-{search_max_y})"
        )
    else:
        print(
            f"Error: No suitable horizontal line found for inner top border in band {search_min_y}-{search_max_y}."
        )
        # Fallback: Use outer edge + fixed offset? Or return None?
        inner_edges["top"] = (
            outer_edges["top"] + expected_border_thickness_px // 2
        )  # Simple fallback
        print(f"  Using fallback inner top: {inner_edges['top']}")
        # return None # Stricter: fail if no line found

    # --- Inner Bottom Edge ---
    search_max_y = outer_edges["bottom"]
    search_min_y = outer_edges["bottom"] - search_band
    bottom_candidates = [
        min(l[0][1], l[1][1])
        for l in H_lines
        if search_min_y < (l[0][1] + l[1][1]) / 2 < search_max_y
    ]
    if bottom_candidates:
        inner_edges["bottom"] = int(
            min(bottom_candidates)
        )  # Innermost is min Y
        print(
            f"Inner border found - Bottom: {inner_edges['bottom']}px (search band {search_min_y}-{search_max_y})"
        )
    else:
        print(
            f"Error: No suitable horizontal line found for inner bottom border in band {search_min_y}-{search_max_y}."
        )
        inner_edges["bottom"] = (
            outer_edges["bottom"] - expected_border_thickness_px // 2
        )
        print(f"  Using fallback inner bottom: {inner_edges['bottom']}")
        # return None

    # --- Inner Left Edge ---
    search_min_x = outer_edges["left"]
    search_max_x = outer_edges["left"] + search_band
    left_candidates = [
        max(l[0][0], l[1][0])
        for l in V_lines
        if search_min_x < (l[0][0] + l[1][0]) / 2 < search_max_x
    ]
    if left_candidates:
        inner_edges["left"] = int(max(left_candidates))  # Innermost is max X
        print(
            f"Inner border found - Left: {inner_edges['left']}px (search band {search_min_x}-{search_max_x})"
        )
    else:
        print(
            f"Error: No suitable vertical line found for inner left border in band {search_min_x}-{search_max_x}."
        )
        inner_edges["left"] = (
            outer_edges["left"] + expected_border_thickness_px // 2
        )
        print(f"  Using fallback inner left: {inner_edges['left']}")
        # return None

    # --- Inner Right Edge ---
    # This will likely be the divider line or the table's right edge
    search_max_x = outer_edges["right"]
    search_min_x = outer_edges["right"] - search_band
    right_candidates = [
        min(l[0][0], l[1][0])
        for l in V_lines
        if search_min_x < (l[0][0] + l[1][0]) / 2 < search_max_x
    ]
    if right_candidates:
        inner_edges["right"] = int(min(right_candidates))  # Innermost is min X
        print(
            f"Inner border found - Right: {inner_edges['right']}px (search band {search_min_x}-{search_max_x})"
        )
    else:
        print(
            f"Error: No suitable vertical line found for inner right border in band {search_min_x}-{search_max_x}."
        )
        inner_edges["right"] = (
            outer_edges["right"] - expected_border_thickness_px // 2
        )
        print(f"  Using fallback inner right: {inner_edges['right']}")
        # return None

    # --- Divider Line ---
    # Search for a strong vertical line between inner_left and inner_right
    # --- Start search further to the right (e.g., 60% across the figure area) ---
    figure_width = inner_edges["right"] - inner_edges["left"]
    # Ensure figure_width is positive before calculating ratio
    if figure_width <= 0:
        print("Error: Invalid left/right inner edges for divider search.")
        # Handle error: estimate divider, or return None from function
        inner_edges["divider"] = inner_edges["left"] + 100  # Arbitrary fallback
    else:
        # Start searching, e.g., 60% of the way from left towards right inner edge
        divider_search_start = inner_edges["left"] + int(figure_width * 0.80)
        # End search slightly before the determined right inner edge
        divider_search_end = (
            inner_edges["right"] - 50
        )  # Keep buffer from right edge

        height = (
            outer_edges["bottom"] - outer_edges["top"]
        )  # Use outer edges for height ref
        min_divider_height = height * 0.5

        divider_candidates = []
        print(
            f"Divider search range: {divider_search_start}px to {divider_search_end}px"
        )
        for l in V_lines:
            x_avg = (l[0][0] + l[1][0]) / 2
            line_len = abs(l[0][1] - l[1][1])
            # Check if the line is within the refined divider region and long enough
            if (
                divider_search_start < x_avg < divider_search_end
                and line_len > min_divider_height
            ):
                # Check if it spans a significant portion vertically within the bounds
                line_y_min = min(l[0][1], l[1][1])
                line_y_max = max(l[0][1], l[1][1])
                # Adjust vertical span check relative to inner edges top/bottom
                if (
                    line_y_min < inner_edges["top"] + height * 0.2
                    and line_y_max > inner_edges["bottom"] - height * 0.2
                ):
                    divider_candidates.append(x_avg)

        if divider_candidates:
            # --- Select the RIGHTMOST candidate ---
            inner_edges["divider"] = int(max(divider_candidates))
            print(
                f"Divider line found at x={inner_edges['divider']}px (selected rightmost)"
            )
        else:
            print(
                "Warning: Could not find clear divider line in refined zone. Estimating."
            )
            # Fallback estimation remains the same, based on determined left/right
            inner_edges["divider"] = int(
                inner_edges["left"]
                + (inner_edges["right"] - inner_edges["left"]) * 0.75
            )

    # Final validation
    if not (
        "top" in inner_edges
        and "bottom" in inner_edges
        and "left" in inner_edges
        and "divider" in inner_edges
        and "right" in inner_edges
        and inner_edges["top"] < inner_edges["bottom"]
        and inner_edges["left"] < inner_edges["divider"] < inner_edges["right"]
    ):
        print(
            "Error: Inner border calculation resulted in invalid or incomplete dimensions."
        )
        return None

    # Rename 'right' to 'table_right' for clarity if needed
    inner_edges["table_right"] = inner_edges.pop("right")

    return inner_edges

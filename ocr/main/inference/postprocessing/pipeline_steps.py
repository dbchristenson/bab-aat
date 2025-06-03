from collections import defaultdict, deque

from ocr.models import Tag


def _get_bbox_extremes(bbox_points: list) -> tuple[float, float, float, float]:
    """Calculates min/max x/y coordinates from bbox points."""
    x_coords = [p[0] for p in bbox_points]
    y_coords = [p[1] for p in bbox_points]
    if not x_coords or not y_coords:  # Should not happen for valid bboxes
        return 0, 0, 0, 0
    return min(x_coords), min(y_coords), max(x_coords), max(y_coords)


def _process_page_detections(
    page_detections: list,  # list of Detection objects for a single page
    document_instance,  # Document model instance
    page_number: int,
) -> list[tuple]:  # list of Tag objects
    """
    Processes detections for a single page to find and create Tags.

    Uses BFS to find connected components based on bounding box overlaps.

    Args:
        page_detections (list): List of Detection objects for a single page.
        document_instance (Document): The Document instance.
        page_number (int): The page number of the document (1-indexed).

    Returns:
        list: List of tuples containing Tag objects and their detections.
    """
    if not page_detections:
        return []

    num_dets = len(page_detections)
    adj = defaultdict(list)
    det_extremes = [_get_bbox_extremes(det.bbox) for det in page_detections]

    for i in range(num_dets):
        for j in range(i + 1, num_dets):
            x_min1, y_min1, x_max1, y_max1 = det_extremes[i]
            x_min2, y_min2, x_max2, y_max2 = det_extremes[j]

            horizontal_overlap = x_min1 <= x_max2 and x_max1 >= x_min2
            vertical_overlap = y_min1 <= y_max2 and y_max1 >= y_min2

            if horizontal_overlap and vertical_overlap:
                adj[i].append(j)
                adj[j].append(i)

    visited = [False] * num_dets
    page_tag_data = []
    for i in range(num_dets):
        if not visited[i]:
            component_indices = []
            q = deque([i])
            visited[i] = True
            while q:
                u_idx = q.popleft()
                component_indices.append(u_idx)
                for v_idx in adj[u_idx]:
                    if not visited[v_idx]:
                        visited[v_idx] = True
                        q.append(v_idx)

            comp_dets = [page_detections[k] for k in component_indices]
            comp_dets.sort(key=lambda d: _get_bbox_extremes(d.bbox)[1])

            merged_text = " ".join([d.text for d in comp_dets])

            all_x = [p[0] for det in comp_dets for p in det.bbox]
            all_y = [p[1] for det in comp_dets for p in det.bbox]
            merged_bbox = [
                [min(all_x), min(all_y)],
                [max(all_x), min(all_y)],
                [max(all_x), max(all_y)],
                [min(all_x), max(all_y)],
            ]
            min_conf = min(d.confidence for d in comp_dets)

            # Assuming Tag class is available globally or imported
            # And that Document model is also available for Tag's FK
            tag = Tag(
                document=document_instance,
                page_number=page_number,
                text=merged_text,
                bbox=merged_bbox,
                algorithm="proximity_merge",
                confidence=min_conf,
            )
            page_tag_data.append((tag, comp_dets))
    return page_tag_data


def merge_touching_detections(detections: list) -> list[tuple]:
    """
    Merge detections with overlapping bounding boxes into
    a single 'tag' detection.

    Some detections may be touching or overlapping, specifically
    in the vertical direction. This function aims to merge detections
    whose bounding boxes top and bottom edges overlap with another
    detection's bounding box top and bottom edges. The text data of the
    detections will be concatenated into a single string and it will
    be organized starting with the top-most detection.

    It is important to note that more than two detections may be stacked
    vertically. For example if 3 detections are stacked vertically, the
    top and the bottom detections may not be touching, but the middle
    detection should link the top and bottom detections together.

    Args:
        detections (list): List of Detection objects to be merged.

    Returns:
        list: List of merged Detection objects.
    """
    if not detections:
        return []

    # Group detections by page_id (using Detection.page.id)
    page_groups = defaultdict(list)
    for det in detections:
        page_groups[det.page.id].append(det)

    tag_data_with_detections = []
    for page_id in page_groups:
        current_page_detections = page_groups[page_id]
        if not current_page_detections:
            continue

        # All detections on a page share the same Page instance and Document
        # and page number.
        doc_instance = current_page_detections[0].page.document
        # Assuming Page model has 'page_number' attribute (1-indexed for Tag)
        p_number = current_page_detections[0].page.page_number

        tags_for_page = _process_page_detections(
            current_page_detections, doc_instance, p_number
        )
        tag_data_with_detections.extend(tags_for_page)

    return tag_data_with_detections

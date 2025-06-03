import re
from collections import defaultdict, deque

from loguru import logger
from spellchecker import SpellChecker

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
        list[tuple]: List of new tag objects with detection composition data.
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


def remove_single_character_detections(
    tag_det_data: list[tuple],
) -> list[tuple]:
    """
    Remove tags that consist of a single character
    """
    logger.info("Removing single character tags from the merged tag data.")

    new_data = []

    for tag, det in tag_det_data:
        if len(tag.text) == 1:
            # Log the removal of single character tags
            logger.info(
                f"Removing tag: {tag.text} on page {tag.page_number} \\"
                "Reason: Single character tag"
            )
            continue
        else:
            new_data.append((tag, det))

    return new_data


def remove_numeric_only_tags(
    tag_det_data: list[tuple],
) -> list[tuple]:
    """
    Remove tags that consist of numeric characters only.

    This includes tags that are purely digits and also tags where there
    are spaces between digits, such as "123 456". Or if there are special
    characters, punctuation, or symbols, such as "123.456". These symbols
    might be the degree symbol, percent sign, bracket }, or similar.
    """
    logger.info("Removing numeric-only tags from the merged tag data.")

    new_data = []

    for tag, det in tag_det_data:
        # Check if the tag text contains any alphabetic characters
        if not any(char.isalpha() for char in tag.text):
            logger.info(
                f"Removing numeric-only tag: {tag.text} on "
                f"page {tag.page_number} Reason: Tag lacks alphabetic chars"
            )
            continue
        else:
            new_data.append((tag, det))

    return new_data


def _skip_EXX_tags(text: str) -> bool:
    """
    Check if the text is an EXX tag.

    EXX tags are typically in the format "EXX" where the X's are digits.
    Args:
        text (str): The text to check.
    Returns:
        bool: True if the text is an EXX tag, False otherwise.
    """
    pattern = r"^[()\[\]/\\]*E\d{2}[()\[\]/\\]*$"
    return bool(re.fullmatch(pattern, text))


def _remove_specified_chars(word: str) -> str:
    """
    Removes specified special characters from a string.

    Args:
        word: The input string.
    Returns:
        The string with specified characters removed.
    """
    chars_to_remove = "(){}[]\\/"
    translation_table = str.maketrans("", "", chars_to_remove)
    return word.translate(translation_table)


def _correct_text_if_needed(
    text_to_check: str,
    spell_checker: SpellChecker,
) -> tuple[str, bool]:
    """
    Spell checks and corrects a single text string based on conditions.

    Args:
        text_to_check (str): The text string to spell check.
        spell_checker (SpellChecker): An instance of the SpellChecker.

    Returns:
        tuple[str, bool]: The corrected text and a boolean indicating
                          if any correction was made.
    """
    words = text_to_check.split()
    corrected_word_list = []
    text_was_changed = False
    min_word_len_for_correction = 3  # Avoid correcting very short words

    for current_word in words:
        # Only attempt to correct words containing letters and of min length
        current_word = _remove_specified_chars(current_word)
        if (
            not any(c.isalpha() for c in current_word)
            or len(current_word) < min_word_len_for_correction
            or _skip_EXX_tags(current_word)
        ):
            corrected_word_list.append(current_word)
            continue

        # spell.correction() returns original word if correct or unknown
        best_candidate = spell_checker.correction(current_word)

        if best_candidate is None:  # Should be rare for non-empty words
            best_candidate = current_word  # Fallback to original

        if best_candidate != current_word:
            corrected_word_list.append(best_candidate)
            text_was_changed = True
        else:
            corrected_word_list.append(current_word)

    if not text_was_changed:
        # Return original text instance if no effective changes
        return text_to_check, False

    return " ".join(corrected_word_list), True


def spell_check_tags(tag_det_data: list[tuple]) -> list[tuple]:
    """
    Spell check the tags and return corrected tags.

    Some strings in tags may be misspelled and need correction. The tags which
    this operation are relevant for are specific:
    - Tags must contain alphabetic characters.
    - Tags must not have a hyphen in them.

    Args:
        tag_det_data (list[tuple]): List of tuples containing Tag objects and
                                    their associated detections.

    Returns:
        list[tuple]: List of corrected tuples.
    """
    logger.info("Spell checking tags.")
    spell = SpellChecker()
    spell.word_frequency.load_dictionary(
        "ocr/main/inference/postprocessing/bumi_words.json"
    )

    new_data = []

    for tag, det in tag_det_data:
        original_text = tag.text

        if "-" in original_text or not any(c.isalpha() for c in original_text):
            new_data.append((tag, det))
            continue
        else:
            corrected_text, text_was_changed = _correct_text_if_needed(
                original_text, spell
            )

            if text_was_changed:
                # Only update tag if the text was actually changed
                tag.text = corrected_text
                logger.info(
                    f"Corrected tag text from '{original_text}' to "
                    f"'{corrected_text}' on page {tag.page_number}."
                )
            else:
                logger.debug(
                    f"No correction needed for tag text: '{original_text}' "
                    f"on page {tag.page_number}."
                )

            new_data.append((tag, det))

    if not new_data:
        logger.info("No tags to spell check or all tags were skipped.")
        return tag_det_data

    return new_data

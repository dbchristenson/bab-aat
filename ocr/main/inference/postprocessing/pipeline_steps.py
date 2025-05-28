def rescale_bbox(bbox: list[list], scale_param: float) -> list:
    """
    Rescale the bounding box coordinates based on the scale parameter
    to fit the original image size. For example, if we scaled up using 4.0
    then the bbox should be divided by 4.0 to get the original size.

    Args:
        bbox (list[list]): The bounding box coordinates to rescale.
        scale_param (float): The scale parameter to use for rescaling.

    Returns:
        list: The rescaled bounding box coordinates.
    """
    rescaled_bbox = []
    for point in bbox:
        if len(point) == 2:
            rescaled_point = [coord / scale_param for coord in point]
            rescaled_bbox.append(rescaled_point)
        else:
            # Handle malformed point if necessary, or raise error
            rescaled_bbox.append(point)  # Or skip
    return rescaled_bbox

from PIL import Image


def get_bbox(result):
    return result[0]


def get_ocr(result):
    return result[1][0]


def get_confidence(result):
    return result[1][1]


def crop_image(image_path, bbox) -> Image:
    """
    Crop the image based on the bounding box.

    Args:
        image_path (str): Path to the image.
        bbox (list): Bounding box coordinates.

    Returns:
        PIL.Image: Cropped image.
    """
    img = Image.open(image_path)
    left = int(bbox[0][0])
    top = int(bbox[0][1])
    right = int(bbox[2][0])
    bottom = int(bbox[2][1])

    cropped_img = img.crop((left, top, right, bottom))
    return cropped_img
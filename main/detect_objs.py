import os
from collections import Counter

BASE_PATH = os.getcwd()


def parse_img_dir(img_dir: str):
    """
    This function parses the image directory and returns a list of image paths.
    When passing img_dir, the working directory is assumed to begin at
    the bab-aat repo root. When assigning img_dir and using the repo
    as a template, the path should begin with data/* and end with a
    directory containing the images.
    """
    data_path = os.path.join(BASE_PATH, img_dir)

    img_paths = [
        os.path.join(data_path, f)
        for f in os.listdir(data_path)
        if f.endswith(".png")
    ]

    return img_paths


def find_image_parent(img_path: str):
    """
    This function finds the parent document of an image.
    The image path is assumed to be of the form:
    data_path/doc_name_{page#}.png

    Page no. is 0-indexed
    """
    if not os.path.isfile(img_path):

        raise (ValueError(f"{img_path} is not a file"))

    # extract doc_name
    # if _ is used in doc_name, this will fail
    doc_name = img_path.split("/")[-1].split("_")[0]

    return doc_name


def apply_network(img_dir: str):
    """
    Apply the network to images in the given directory. The images
    are converted from PDF to PNG page by page.
    """

    # Get all images
    img_paths = parse_img_dir(img_dir)

    parents = []

    for path in img_paths:
        # Because each page is an image, we need to find the parent
        # document to link the page to the document
        image_parent = find_image_parent(path)

        parents.append(image_parent)

    # count
    counter = Counter(parents)
    print("Document counts:")
    print("Total documents:", counter.total())
    print("Unique documents:", len(set(parents)))
    print("Document counts by name:")
    for doc_name, count in counter.items():
        print(f"{doc_name}: {count}")
    return


if __name__ == "__main__":
    # Get the current working directory
    apply_network("olombendo_output")

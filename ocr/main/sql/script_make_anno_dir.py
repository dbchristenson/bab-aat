import argparse
import os
import random

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babaatsite.settings")
django.setup()

from ocr.models import Document, Page, Truth, Vessel  # noqa E402


def get_kraken_without_truth():
    """
    This function queries the documents table and returns all Kraken documents
    which do not have a truth associated with them. This is useful for
    identifying documents which need to be annotated.
    """

    relevant_documents = Document.objects.filter(vessel_id=1).exclude(
        document_number__in=Truth.objects.values_list(
            "document_number", flat=True
        )
    )

    return relevant_documents


def get_vessel_documents_without_truth(vessel: Vessel):
    """
    This function queries the documents table and returns all documents
    associated with the given vessel which do not have a truth associated
    with them. This is useful for identifying documents which need to be
    annotated.
    """
    relevant_documents = Document.objects.filter(vessel=vessel).exclude(
        document_number__in=Truth.objects.values_list(
            "document_number", flat=True
        )
    )
    return relevant_documents


def get_pages_for_documents(vessel: Vessel) -> list:
    """
    This function queries the pages table and returns all pages associated with
    the documents returned from get_kraken_without_truth(). This is useful for
    identifying pages which need to be annotated.
    """

    relevant_documents = get_vessel_documents_without_truth(vessel)
    relevant_pages = []

    for doc in relevant_documents:
        pages = Page.objects.filter(document=doc).order_by("page_number")
        relevant_pages.extend(pages)

    # Sample 100 pages with seed 42 on sorted list
    relevant_pages = sorted(
        relevant_pages, key=lambda x: x.document.document_number
    )
    random.seed(42)
    relevant_pages = random.sample(
        relevant_pages,
        100,
    )

    return relevant_pages


def make_anno_dir(pages: list, output_dir: str) -> None:
    """
    This function creates a directory and populates it with the images
    of the pages which need to be annotated. The directory is named
    by the output_dir argument and the pages are named by their
    document_number and page_number.
    """

    os.makedirs(output_dir, exist_ok=True)

    for page in pages:
        image_path = page.image.path
        image_name = f"{page.document.document_number}_{page.page_number}.jpg"
        output_path = os.path.join(output_dir, image_name)

        # Copy the image to the output directory
        with open(image_path, "rb") as src_file:
            with open(output_path, "wb") as dest_file:
                dest_file.write(src_file.read())

    print(f"Annotated images saved to {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a directory for annotating pages."
    )
    parser.add_argument(
        "--vessel",
        type=str,
        required=True,
        help="The name of the vessel to filter documents.",
    )
    args = parser.parse_args()

    try:
        vessel = Vessel.objects.get(name=args.vessel)
    except Vessel.DoesNotExist:
        print(f"Vessel '{args.vessel}' does not exist.")
        exit(1)
    pages = get_pages_for_documents(vessel)
    output_dir = os.path.join("resources", "need_annotating", vessel.name)
    make_anno_dir(pages, output_dir)

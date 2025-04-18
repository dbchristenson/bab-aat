import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babaatsite.settings")
django.setup()

from ocr.models import Document, Page, Truth  # noqa E402


def get_kraken_with_truth():
    """
    This function queries the documents table and returns all Kraken documents
    which have a truth associated with them.
    """

    relevant_documents = Document.objects.filter(
        vessel_id=1,
        document_number__in=Truth.objects.values_list(
            "document_number", flat=True
        ),
    )

    print(
        f"Found {relevant_documents.count()} documents with truth associated."
    )

    return relevant_documents


def get_pages_for_documents() -> list:
    """
    This function queries the pages table and returns all pages associated with
    the documents returned from get_kraken_without_truth(). This is useful for
    identifying pages which need to be annotated.
    """

    relevant_documents = get_kraken_with_truth()
    relevant_pages = []

    for doc in relevant_documents:
        pages = Page.objects.filter(document=doc).order_by("page_number")
        relevant_pages.extend(pages)

    return relevant_pages


def make_eval_dir(pages: list, output_dir: str) -> None:
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


pages = get_pages_for_documents()
output_dir = os.path.join("resources", "eval_pages")
make_eval_dir(pages, output_dir)

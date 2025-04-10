import argparse
import datetime as dt
import logging
import os

import pypdfium2 as pdfium
from django.core.files import File

# new imports
from django.db import IntegrityError
from django.db.models import Q

from babaatsite.settings import BASE_DIR
from ocr.main.utils.configs import with_config
from ocr.main.utils.loggers import basic_logging
from ocr.main.utils.page_to_img import create_img_and_pad_divisible_by_32
from ocr.models import Document, Page, Vessel

# Setup logging
basic_logging("pdf_img_pipeline")


def resolve_dir_path(dir_path: str, absolute_path: bool) -> str:
    if absolute_path:
        return dir_path
    else:
        return os.path.join(BASE_DIR, dir_path)


def save_document(file: File, vessel: Vessel) -> int | None:
    """
    Saves or updates a Document record in the database using an uploaded file
    and an associated Vessel. Checks for an existing document with the same
    vessel, file name, or derived document number. Compares metadata (file
    size and last modified timestamp). If an existing document is found and
    its metadata differs, the document is deleted and a new one is created.
    Otherwise, the document is not re-saved.

    Args:
        file (File): The uploaded file object.
        vessel (Vessel): The Vessel instance associated with the document.

    Returns:
        A list of integers representing the IDs of the saved or updated
        Document records.

        None if the document already exists with identical metadata.

    Raises:
        IntegrityError: If database constraints are violated during saving.
        OSError: If file metadata cannot be read.

    Notes:
        - The document_number is derived from the file name.
        - As the uploaded file might not have an inherent last-modified time,
          the current timestamp is used.
        - This function relies on Django’s FileField storage to handle moving
          the file from a temporary to a permanent location.
    """
    file_name = file.name
    file_size = file.size
    last_modified = dt.datetime.now()  # Using current time as last_modified
    document_number = file_name.split(".")[0]

    # Check if a document with the same vessel and file name or document number exists. # noqa 501
    existing_doc_qs = Document.objects.filter(vessel=vessel).filter(
        Q(name=file_name) | Q(document_number=document_number)
    )

    if existing_doc_qs.exists():
        existing_doc = existing_doc_qs.first()
        # Compare file metadata; note that last_modified here is newly
        # generated, so if you need a more accurate check, you might
        # need to store the original mod time.
        size_change = existing_doc.file_size != file_size
        modified_change = existing_doc.last_modified != last_modified
        if size_change or modified_change:
            existing_doc.delete()
            logging.info(
                f"Document '{file_name}' has changed (size or modification time); deleting existing record."  # noqa 501
            )
        else:
            logging.info(
                f"Document '{file_name}' already exists with identical metadata; skipping save."  # noqa 501
            )
            return

    # Django's FileField will handle saving the file permanently.
    new_document = Document(
        name=file_name,
        vessel=vessel,
        document_number=document_number,
        file=file,
        file_size=file_size,
        last_modified=last_modified,
    )
    new_document.save()
    logging.info(f"Document '{file_name}' added to the database.")

    return new_document.id


def get_pdf_paths(
    dir: str,
    absolute_path: bool = False,
    max_depth: int = 10,
    min_file_size: int = 1,
    max_file_size: int = float("inf"),
) -> list[str]:
    """
    Recursively finds all PDFs in a directory, saves to DB, returns full paths.

    Scans directory for PDFs, verifies each file, stores in database.
    Returns list of full paths to found PDF files.

    Args:
        dir: Directory to search (relative or absolute path).
        absolute_path: If True, treats 'dir' as absolute path. If False,
            resolves relative to current working directory.
        max_depth: Maximum depth to search for PDFs (default: 10).
        min_file_size: Minimum file size in bytes to consider (default: 1).
        max_file_size: Maximum file size in bytes to consider (default: inf).

    Returns:
        List of full paths to found PDF files.

    Raises:
        AssertionError: If no PDFs found in directory.

    Notes:
        - Only processes '.pdf' files (case-sensitive)
        - Logs warnings for non-file entries (e.g., directories)
        - Auto-saves documents via save_document()
    """
    pdf_data_dir = resolve_dir_path(dir, absolute_path)
    full_pdf_paths = []

    for dirpath, _, filenames in os.walk(pdf_data_dir):
        base_path_length = len(pdf_data_dir)
        current_depth = dirpath[base_path_length:].count(os.sep)

        # Skip if beyond max depth
        if max_depth is not None and current_depth > max_depth:
            continue

        for filename in filenames:
            if filename.lower().endswith(".pdf"):
                full_path = os.path.join(dirpath, filename)

                # Skip if not a file
                if not os.path.isfile(full_path):
                    logging.warning(f"Skipping non-file: {full_path}")
                    continue

                # Check file size
                file_size = os.path.getsize(full_path)
                if not (min_file_size <= file_size <= max_file_size):
                    logging.info(
                        f"Skipping {filename} - size {file_size} bytes "
                        f"(outside range {min_file_size}-{max_file_size})"
                    )
                    continue

                full_pdf_paths.append(full_path)
                save_document(filename, full_path)

    assert full_pdf_paths, (
        f"No PDF files found in {pdf_data_dir} matching criteria "
        f"(depth<={max_depth}, size {min_file_size}-{max_file_size} bytes)"
    )

    return full_pdf_paths


def check_already_converted(pdf_path: str) -> bool:
    """
    Check if a PDF has already been fully converted to images.

    Args:
        pdf_path: Path to the PDF file to check

    Returns:
        bool: True if all pages are already converted and in database,
              False otherwise
    """
    file_name = os.path.basename(pdf_path)
    doc = Document.objects.filter(Document.name == file_name)

    if not doc:
        return False

    page_count = Page.objects.filter(Page.document == doc).count()

    try:
        pdf = pdfium.PdfDocument(pdf_path)
        num_pages = len(pdf)
        pdf.close()
        return page_count == num_pages
    except Exception as e:
        logging.error(
            f"Could not open PDF {pdf_path} for page count verification: {e}"
        )
        return False


def save_img_to_db(parent_doc: Document, page_num: int, img_path: str) -> None:
    """
    Saves the image file to the database by creating a Page record using the
    image field from the Page model. The image file is opened, wrapped in a
    Django File object, and passed to the ImageField.

    Args:
        parent_doc (Document): The Document object associated with the PDF.
        page_num (int): The page number (0-indexed) of the PDF being processed.
        img_path (str): The filesystem path to the image file to save.

    Raises:
        IntegrityError: If database constraints are violated during creation.
    """
    try:
        with open(img_path, "rb") as f:
            django_file = File(f, name=os.path.basename(img_path))
            Page.objects.create(
                document=parent_doc, page_number=page_num, image=django_file
            )
        logging.info(f"Page {page_num} of {parent_doc.name} saved.")
    except IntegrityError as e:
        logging.error(
            f"Error saving page {page_num} of {parent_doc.name}: {e}"
        )  # noqa 501
    except FileNotFoundError as e:
        logging.error(
            f"File not found for page {page_num} of {parent_doc.name}: {e}"
        )
        # Remove from database if file not found
        parent_doc.delete()
        logging.info(
            f"Deleted Document {parent_doc.name} due to missing image file."
        )


def convert_pdf(
    input_data,  # Accepts str | pathlib.Path | bytes | BinaryIO etc.
    parent_doc: Document,
    output_dir: str,
    scale: int = 4,
) -> None:
    """
    Convert a single PDF to images while tracking state in the database.

    Args:
        input_data (str | pathlib.Path | bytes | typing.BinaryIO):
            The PDF input as a file path, bytes, or any file-like object.
        parent_doc (Document): Document object for the parent PDF.
        output_dir (str): Directory to save converted images.
        scale (int): Scaling factor for image conversion (default: 4).
    """
    # Derive file_name and base_name from the Document instance
    file_name = parent_doc.name
    base_name = os.path.splitext(file_name)[0]

    # If input_data is a file-like object, ensure the pointer is at the beginning.  # noqa 501
    try:
        input_data.seek(0)
    except Exception:
        pass

    pdf = pdfium.PdfDocument(input_data)

    for i in range(len(pdf)):
        page = pdf[i]
        img = create_img_and_pad_divisible_by_32(page, scale=scale)
        new_name = f"{base_name}_{i}.png"
        new_path = os.path.join(output_dir, new_name)
        img.save(new_path)
        logging.info(f"Page {i} of {file_name} saved as image.")
        save_img_to_db(parent_doc, i, new_path)

    pdf.close()


def convert_pdfs(pdf_paths: list[str], output_dir: str, scale: int = 4):
    """
    Convert PDFs to images while tracking state in database.

    Args:
        pdf_paths: List of PDF file paths to convert
        output_dir: Directory to save converted images
        scale: Scaling factor for image conversion (default: 4)

    Raises:
        Document.DoesNotExist: If a document is not found in the
        database when trying to convert it
    """
    for path in pdf_paths:
        if check_already_converted(path):
            logging.info(f"{path} has already been converted. Skipping.")
            continue

        file_name = os.path.basename(path)
        base_name = os.path.splitext(file_name)[0]

        try:
            parent_doc = Document.objects.get(Document.name == file_name)
            convert_pdf(
                path, parent_doc, base_name, file_name, output_dir, scale=scale
            )
        except Document.DoesNotExist:
            logging.error(f"Document {file_name} not found in database.")
            raise ValueError(f"Document {file_name} not found in database.")

        except Exception as e:
            logging.error(f"Failed to convert {file_name}: {e}")
            continue

    return


@with_config
def main_pipeline(config=None):
    pdf_dir = config.get("pdf_dir")
    output_dir = config.get("output_dir")
    scale = config.get("scale")
    absolute_path = config.get("absolute_path")
    max_depth = config.get("max_depth")
    min_file_size = config.get("min_file_size_kb") * 1024
    max_file_size = config.get("max_file_size_kb") * 1024

    os.makedirs(output_dir, exist_ok=True)
    pdf_paths = get_pdf_paths(
        pdf_dir,
        absolute_path=absolute_path,
        max_depth=max_depth,
        min_file_size=min_file_size,
        max_file_size=max_file_size,
    )
    convert_pdfs(pdf_paths, output_dir, scale=scale)

    logging.info("PDFs converted to images.")

    return


# /olombendo_src/original_no_ocr/P&ID/Process/
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process PDFs to images.")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to the configuration file.",
        default=os.path.join(BASE_DIR, "config.json"),
    )
    args = parser.parse_args()

    main_pipeline(config=args.config)

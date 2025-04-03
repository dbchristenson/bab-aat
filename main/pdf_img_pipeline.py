import argparse
import datetime as dt
import logging
import os

import pypdfium2 as pdfium
from models import Document, Page
from peewee import IntegrityError
from utils.configs import with_config
from utils.page_to_img import create_img_and_pad_divisible_by_32

# Not relevant for usage on cloud/production
BASE_DIR = "/Users/dbchristenson/Desktop/python/bab-aat/bab-aat"
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")

# Setup logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("main/logs/pdf_img_pipeline.log"),  # Log to a file
        logging.StreamHandler(),  # Log to the console
    ],
)


def resolve_dir_path(dir_path: str, absolute_path: bool) -> str:
    if absolute_path:
        return dir_path
    else:
        return os.path.join(DATA_DIR, dir_path)


def save_document(file_name: str, file_path: str) -> None:
    """
    Saves or updates a document record in the database.

    Checks if document exists and compares metadata (size, modification time).
    If document is new or changed, creates/updates the database record.
    Logs all operations and errors.

    Args:
        file_name: Name of the document file (including extension).
        file_path: Full absolute path to the document file.

    Raises:
        IntegrityError: If database constraints are violated during save.
        OSError: If file metadata cannot be read (implicit from os calls).

    Notes:
        - Performs atomic update by deleting and recreating changed documents
        - Compares both file size and last modified timestamp for changes
        - Logs at INFO level for normal operations, ERROR for failures
        - Uses Document model which must have fields: name, file_path,
          file_size, and last_modified
    """
    try:
        # get file metadata
        file_size = os.path.getsize(file_path)
        last_modified = dt.datetime.fromtimestamp(os.path.getmtime(file_path))

        existing_doc = Document.get_or_none(
            (Document.name == file_name) | (Document.file_path == file_path)
        )

        if existing_doc:
            # Has the document changed?
            size_change = existing_doc.file_size != file_size
            modified_change = existing_doc.last_modified != last_modified
            if size_change or modified_change:
                existing_doc.delete_instance()
                logging.info(f"Document {file_name} has changed, deleting.")
            else:
                logging.info(f"Document {file_name} already exists, skipping.")
                return

        document_number = file_name.split(".")[0]

        # Create a new document
        new_document = Document(
            name=file_name,
            document_number=document_number,
            file_path=file_path,
            file_size=file_size,
            last_modified=last_modified,
        )
        new_document.save()
        logging.info(f"Document {file_name} added to the database.")

    except IntegrityError as e:
        logging.error(f"Error saving document {file_name}: {e}")


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
    doc = Document.get_or_none(Document.name == file_name)

    if not doc:
        return False

    page_count = Page.select().where(Page.document == doc).count()

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


def save_img_to_db(parent_doc: Document, page_num: int, img_path: str):
    """
    Save the image to the output directory and add the page to the database.

    Args:
        parent_doc: Document object for the parent PDF
        page_num: Page number of the image
        img_path: Path to the image file

    Raises:
        IntegrityError: If database constraints are violated during
    """
    try:
        Page.create(
            document=parent_doc, page_number=page_num, img_path=img_path
        )
        logging.info(f"Page {page_num} of {parent_doc.name} saved.")
    except IntegrityError as e:
        logging.error(f"Error with page {page_num} of {parent_doc.name}: {e}")


def convert_pdf(
    path: str,
    parent_doc: Document,
    base_name: str,
    file_name: str,
    output_dir: str,
    scale: int = 4,
):
    """
    Convert a single PDF to images while tracking state in database.

    Args:
        pdf: Pdfium PDF object to convert
        parent_doc: Document object for the parent PDF
        base_name: Base name of the PDF file
        file_name: Full name of the PDF file with the extension
        output_dir: Directory to save converted images
        scale: Scaling factor for image conversion (default: 4)
    """
    pdf = pdfium.PdfDocument(path)

    for i in range(len(pdf)):
        page = pdf[i]
        img = create_img_and_pad_divisible_by_32(page, scale=scale)
        new_name = f"{base_name}_{i}.png"
        new_path = os.path.join(output_dir, new_name)

        # Save img to output and data to db
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
            parent_doc = Document.get(Document.name == file_name)
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

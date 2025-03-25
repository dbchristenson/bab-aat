import argparse
import datetime as dt
import glob
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

        # Create a new document
        new_document = Document(
            name=file_name,
            file_path=file_path,
            file_size=file_size,
            last_modified=last_modified,
        )
        new_document.save()
        logging.info(f"Document {file_name} added to the database.")

    except IntegrityError as e:
        logging.error(f"Error saving document {file_name}: {e}")


def get_pdf_paths(
    dir: str, output_dir: str, absolute_path: bool = False
) -> list[str]:
    """Finds all PDFs in a directory, saves to DB, returns full paths.

    Scans directory for PDFs, verifies each file, stores in database.
    Returns list of full paths to found PDF files.

    Args:
        dir: Directory to search (relative or absolute path).
        output_dir: Directory for processed files/output.
        absolute_path: If True, treats 'dir' as absolute path. If False,
            resolves relative to current working directory.

    Returns:
        List of full paths to found PDF files.

    Raises:
        AssertionError: If no PDFs found in directory.

    Notes:
        - Only processes '.pdf' files (case-sensitive)
        - Logs warnings for non-file entries (e.g., directories)
        - Auto-saves documents via save_document()
    """

    # Setup and verify the PDF data directory
    pdf_data_dir = resolve_dir_path(dir, absolute_path)

    pdf_paths = [f for f in os.listdir(pdf_data_dir) if f.endswith(".pdf")]
    assert len(pdf_paths) > 0, f"No PDF files found in {pdf_data_dir}"

    # Collect the full paths of the PDF files
    full_pdf_paths = []

    for path in pdf_paths:
        new_path = os.path.join(pdf_data_dir, path)

        # Check if the path is a file
        if os.path.isfile(new_path):
            full_pdf_paths.append(new_path)
        else:
            logging.warning(f"{new_path} is not a file")
            continue

        # Add the document to the database, path acts as the file's name
        save_document(path, new_path)

    return full_pdf_paths


def check_already_converted(path: str, output_dir: str) -> tuple[bool, str]:
    file_name = path.split("/")[-1]
    pattern = os.path.join(output_dir, f"{file_name[:-2]}*.png")

    converted = glob.glob(pattern)
    if converted:
        logging.info(f"{path} already converted, skipping...")

    return converted, file_name


def save_img(parent_doc: Document, page_num: int, img_path: str):
    """
    Save the image to the output directory and add the page to the database.
    """

    # Save the image
    new_page = Page(
        document=parent_doc, page_number=page_num, img_path=img_path
    )
    new_page.save()
    logging.info(f"Page {page_num} of {parent_doc.name} saved.")


def convert_pdfs(pdf_paths: list, output_dir: str, scale: int = 4):

    for path in pdf_paths:
        file_name = path.split("/")[-1]
        base_name = file_name.split(".")[0]
        pdf = pdfium.PdfDocument(path)

        for i, page in enumerate(pdf):
            # Convert the page to an image
            img = create_img_and_pad_divisible_by_32(page, scale=scale)

            # Save the image
            new_name = f"{base_name}_{i}.png"
            new_path = os.path.join(output_dir, new_name)
            img.save(new_path)
            logging.info(f"Page {i} of {file_name} saved as {new_name}.")

            # Save the image to the database
            parent_doc = Document.get_or_none(Document.name == file_name)
            save_img(parent_doc, i, new_path)

        pdf.close()

    return


@with_config
def main_pipeline(config=None):
    pdf_dir = config.get("pdf_dir")
    output_dir = config.get("output_dir")
    scale = config.get("scale")
    absolute_path = config.get("absolute_path")

    os.makedirs(output_dir, exist_ok=True)
    pdf_paths = get_pdf_paths(pdf_dir, output_dir, absolute_path=absolute_path)
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

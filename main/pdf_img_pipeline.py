import argparse
import glob
import logging
import os

import pypdfium2 as pdfium
from models import Document, Page
from utils.configs import with_config
from utils.page_to_img import create_img_and_pad_divisible_by_32

BASE_DIR = "/Users/dbchristenson/Desktop/python/bab-aat/bab-aat"
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")

# Setup logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file
        logging.StreamHandler(),  # Log to the console
    ],
)


def check_already_converted(path: str, output_dir: str) -> tuple[bool, str]:
    file_name = path.split("/")[-1]
    pattern = os.path.join(output_dir, f"{file_name[:-2]}*.png")

    converted = glob.glob(pattern)
    if converted:
        logging.info(f"{path} already converted, skipping...")

    return converted, file_name


def save_document(file_name: str, file_path: str) -> None:
    """
    Save a document to the database.
    """
    new_document = Document(name=file_name, file_path=file_path)
    new_document.save()
    logging.info(f"Document {file_name} added to the database.")


def get_pdf_paths(
    dir: str, output_dir: str, absolute_path: bool = False
) -> list[str]:
    """
    Get the paths of all PDF files in the specified directory. When working
    locally, I already defined a base and data directory. When
    working elsewhere, define the absolute path to the directory containing
    the PDF files.
    """

    # Setup and verify the PDF data directory
    if absolute_path:
        pdf_data_dir = dir
    else:
        pdf_data_dir = os.path.join(DATA_DIR, dir)

    pdf_paths = [f for f in os.listdir(pdf_data_dir) if f.endswith(".pdf")]
    assert len(pdf_paths) > 0, f"No PDF files found in {pdf_data_dir}"

    # Collect the full paths of the PDF files
    full_pdf_paths = []

    for path in pdf_paths:
        # Check if the PDF defined by the path already has been converted
        converted, file_name = check_already_converted(path, output_dir)
        if converted:
            continue

        new_path = os.path.join(pdf_data_dir, path)

        # Check if the path is a file
        if os.path.isfile(new_path):
            full_pdf_paths.append(new_path)
        else:
            logging.warning(f"{new_path} is not a file")
            continue

        # Add the document to the database
        save_document(file_name, new_path)

    return full_pdf_paths


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
            parent_doc = Document.get(Document.name == file_name)
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

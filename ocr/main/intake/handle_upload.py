import logging
import os
import zipfile

from django.core.files import File
from django.db import IntegrityError

from babaatsite.settings import MEDIA_ROOT
from ocr.main.intake.pdf_img_pipeline import convert_pdf, save_document
from ocr.main.utils.loggers import basic_logging
from ocr.models import Document, Vessel

basic_logging(__name__)


def handle_pdf(file: File, vessel_obj: Vessel | None, output: str) -> None:
    """
    Handle the uploaded PDF file. This function processes the PDF file,
    creates a Document object, and saves the PDF file to the server.
    It also creates Page objects for each page in the PDF and saves
    images of the pages to the server.

    Args:
        file (File): The uploaded PDF file.
        vessel_obj (Vessel): The Vessel object associated with the document.
        output (str): The output directory where the PDF and images are saved.
    """

    try:
        document_id = save_document(file, vessel_obj)
    except IntegrityError as e:
        logging.error(f"Error saving document '{file.name}': {e}")
        raise

    # If document_id == None then the document was already saved
    # and has been processed. We don't need to do anything else.
    if not document_id:
        logging.info(
            f"Document '{file.name}' already exists. No further processing required."  # noqa 501
        )
        return

    document = Document.objects.get(id=document_id)

    upload_directory = os.path.join(MEDIA_ROOT, "pages")
    os.makedirs(upload_directory, exist_ok=True)

    convert_pdf(file, document, upload_directory)

    return document_id


def unzip_file(zip_path: str) -> str:
    """
    Unzips the given zip file to the specified directory.

    Args:
        zip_path (str): The path to the zip file.
        extract_to (str): The directory where the files will be extracted.

    Returns:
        str: The path to the directory where the files were extracted.
    """
    if not zipfile.is_zipfile(zip_path):
        error_msg = f"File at {zip_path} is not a valid zip file."
        logging.error(error_msg)
        raise ValueError(error_msg)

    # Construct the destination directory path
    base_dir = os.path.dirname(zip_path)
    file_base = os.path.splitext(os.path.basename(zip_path))[0]
    dest_dir = os.path.join(base_dir, "extracted", file_base)
    os.makedirs(dest_dir, exist_ok=True)

    # Extract the zip file contents to the destination directory
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(dest_dir)
        logging.info(f"Extracted zip file to {dest_dir}")
    except Exception as e:
        logging.error(f"Error extracting zip file at {zip_path}: {e}")
        raise

    return dest_dir


def get_pdf_file_objects(directory_path: str) -> list[File]:
    """
    Walks through the given directory (and subdirectories) and returns a list
    of Django File objects for every PDF file found.

    Args:
        zip_path (str): The path to the zip file containing the pdfs.

    Returns:
        List[File]: A list of Django File objects wrapping each PDF file.
    """
    pdf_files = []
    # Recursively walk the directory
    for root, dirs, files in os.walk(directory_path):
        for filename in files:
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(root, filename)
                # Open the file in binary mode
                f = open(file_path, "rb")
                # Wrap it in Django's File object
                # (remember, the caller must later close it)
                django_file = File(f, name=filename)
                pdf_files.append(django_file)
    return pdf_files


def get_detections(document_ids: list[int]) -> list[dict]:
    return


def handle_zip(file: File, vessel_obj: Vessel | None, output: str) -> None:
    """
    Unzips the uploaded ZIP file to the media directory and processes each PDF
    file.

    Args:
        file (File): The uploaded ZIP file.
        vessel_obj (Vessel): The Vessel object associated with the document.
        output (str): The output directory where the PDF and images are saved.
    """
    # Unzip the file to the media directory
    extracted_directory = unzip_file(file.temporary_file_path())
    pdf_files = get_pdf_file_objects(extracted_directory)

    for pdf_file in pdf_files:
        # Save the PDF file to the server
        try:
            handle_pdf(pdf_file, vessel_obj, output)
        except IntegrityError as e:
            logging.error(f"Error saving document '{pdf_file.name}': {e}")
            raise

        pdf_file.close()  # Close the file after processing

    return


def handle_uploaded_file(file: File, vessel_id: int) -> None:
    """
    Handle the uploaded file. This function processes the uploaded file,
    which may be a pdf or a zip file. From a pdf, it creates a document
    and page objects. From a zip file, it extracts the pdfs and populates
    the Document table with the pdfs and then populates the Page table
    with images of the pdfs' pages. Finally we also create detections
    for each new page we create.


    Args:
        file (File): The uploaded file.
        vessel_id (int): The ID of the vessel associated with the document.
    """
    vessel_obj = Vessel.objects.filter(id=vessel_id).first()
    file_ext = file.name.split(".")[-1].lower()  # Apparently this is not safe
    logging.warning(
        "Collecting file extension using potentially vulnerable method in handle_upload.py"  # noqa 501
    )

    upload_directory = os.path.join(MEDIA_ROOT, "documents")
    os.makedirs(upload_directory, exist_ok=True)

    # Save file, pages to the server
    if file_ext == "pdf":
        handle_pdf(file, vessel_obj, upload_directory)
    else:
        handle_zip(file, vessel_obj, upload_directory)

    # OCR Inference on the pages
    # TODO

    return

import logging
import os
import uuid
import zipfile

from django.core.files import File

from babaatsite.settings import MEDIA_ROOT
from ocr.main.utils.loggers import basic_logging
from ocr.models import Vessel
from ocr.tasks import process_pdf_task

basic_logging(__name__)


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

    # Delete the zip file after extraction
    try:
        os.remove(zip_path)
        logging.info(f"Deleted zip file at {zip_path}")
    except Exception as e:
        logging.error(f"Error deleting zip file at {zip_path}: {e}")

    return dest_dir


def get_detections(document_ids: list[int]) -> list[dict]:
    return


def _save_in_chunks(
    django_file: File, dest_path: str, chunk_size: int = 64 * 1024
):
    """
    Write an uploaded file to disk in chunks to avoid large memory usage.
    """
    with open(dest_path, "wb") as out:
        for chunk in django_file.chunks(chunk_size):
            out.write(chunk)

    return dest_path


def _collect_pdfs(directory_path):
    """
    Return a flat list of all pdf file paths under directory_path (disk paths).
    """
    pdfs = []
    for root, _, files in os.walk(directory_path):
        for fn in files:
            if fn.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, fn))
    return pdfs


def handle_uploaded_file(django_file: File, vessel_name: str) -> None:
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
    vessel_obj = Vessel.objects.filter(name=vessel_name).first()
    vessel_id = vessel_obj.id

    upload_directory = os.path.join(MEDIA_ROOT, "documents")
    os.makedirs(upload_directory, exist_ok=True)

    # Persist the raw upload to disk
    unique_filename = f"{uuid.uuid4().hex}_{django_file.name}"
    disk_path = os.path.join(upload_directory, unique_filename)
    _save_in_chunks(django_file, disk_path)

    # Gather PDF files
    ext = django_file.name.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        pdf_paths = [disk_path]
    else:
        # unzip then collect PDFs
        extract_dir = os.path.splitext(disk_path)[0]
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(disk_path, "r") as zf:
            zf.extractall(extract_dir)
        os.remove(disk_path)
        pdf_paths = _collect_pdfs(extract_dir)

    # Chunk list to avoid broker overload
    chunk_size = 20
    task_ids = []
    for i in range(0, len(pdf_paths), chunk_size):
        chunk = pdf_paths[i : i + chunk_size]  # noqa 203
        for pdf_path in chunk:
            tid = process_pdf_task.delay(
                pdf_path, vessel_id, upload_directory
            )  # noqa E501
            task_ids.append(tid)

    return task_ids

    # OCR Inference on the pages
    # TODO

    return

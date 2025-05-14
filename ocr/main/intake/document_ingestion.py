import datetime as dt
import logging

from django.core.files import File
from django.db.models import Q

from ocr.main.utils.loggers import basic_logging
from ocr.models import Document, Vessel

# Setup logging
basic_logging("pdf_img_pipeline")


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
    file_name = file.name.strip()
    file_size = file.size
    last_modified = dt.datetime.now()  # Using current time as last_modified
    document_number = file_name.split(".")[0].strip()

    if "_" in document_number:
        document_number = document_number.split("_")[0]

    # Check if a document with the same vessel and file name or document number exists. # noqa 501
    existing_doc_qs = Document.objects.filter(vessel=vessel).filter(
        Q(name=file_name) | Q(document_number=document_number)
    )

    if existing_doc_qs.exists():
        existing_doc = existing_doc_qs.first()
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

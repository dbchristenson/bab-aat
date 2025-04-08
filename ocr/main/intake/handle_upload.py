from django.core.files import File

from ocr.models import Document, Vessel


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

    vessel_obj = Vessel.objects.get(id=vessel_id)

    return

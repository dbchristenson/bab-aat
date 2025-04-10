import logging

from django.http import HttpResponse
from django.shortcuts import render

from ocr.forms import UploadFileForm
from ocr.main.intake.handle_upload import handle_uploaded_file
from ocr.main.utils.loggers import basic_logging
from ocr.models import Detection, Document, Page

basic_logging(__name__)


# Create your views here.
def index(request):
    """
    Render the index page.
    """

    return HttpResponse("Welcome to the OCR API!")


def upload(request):
    """
    Render the upload page. Here users can upload individual pdf documents
    or compressed zip files for processing. Processing involves extracting
    data from the documents and storing it in a database.
    """

    if request.method == "POST":
        logging.info("Received a POST request for file upload.")
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            logging.info("Form is valid. Processing file upload.")
            vessel_id = form.cleaned_data["vessel"]
            file = form.cleaned_data["file"]

            try:
                handle_uploaded_file(file, vessel_id)
            except Exception as e:
                logging.error(f"Error processing file: {e}")
                return render(request, "upload.html", {"form": form})

            return render(request, "upload_success.html")
        else:
            logging.error("Form is invalid.")
            return render(request, "upload.html", {"form": form})
    else:
        form = UploadFileForm()
        # Render the form for file upload
        return render(request, "upload.html", {"form": form})


def upload_success(request):
    """
    Render the upload success page.
    """
    return render(request, "upload_success.html")


def documents(request):
    """
    Render the documents page. This page displays all the documents
    that have been uploaded. Documents are uploaded to the db before
    their detections are fully processed and therefore can be viewed
    before the processing is complete.
    """

    documents = Document.objects.all()

    context = {
        "documents": documents,
    }

    return render(request, "documents.html", context)

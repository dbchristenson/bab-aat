from django.http import HttpResponse
from django.shortcuts import render

from ocr.main.intake.pdf_img_pipeline import main_pipeline
from ocr.models import Detection, Document, Page


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
        # Handle file upload and processing here
        pass

    return render(request, "ocr/upload.html")

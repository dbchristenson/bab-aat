from django.http import HttpResponse
from django.shortcuts import render

from ocr.forms import UploadFileForm
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
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # TODO Process some shit
            return HttpResponse("File uploaded successfully!")
    else:
        form = UploadFileForm()
        # Render the form for file upload
        template = "upload.html"
        return render(request, template, {"form": form})

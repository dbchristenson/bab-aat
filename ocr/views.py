import logging

from django.http import HttpResponse
from django.shortcuts import redirect, render

from ocr.forms import DeleteDocumentsFromVesselForm, UploadFileForm
from ocr.main.intake.handle_upload import handle_uploaded_file
from ocr.main.utils.draw_detections import draw_detections
from ocr.main.utils.loggers import basic_logging
from ocr.models import Detection, Document, Page, Vessel

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
    Render the documents page with filtering options.
    Displays all uploaded documents, and allows filtering
    by vessel and document number.

    Query Parameters:
        vessel: (optional) Vessel id to filter on.
        document_number: (optional) Substring to filter the document number.

    Context:
        documents: QuerySet of filtered Document objects.
        vessels: List of all Vessel objects (for dropdown population).
    """
    selected_vessels = request.GET.getlist("vessels")
    documents = Document.objects.all()
    if selected_vessels:
        documents = documents.filter(vessel__id__in=selected_vessels)
    doc_number = request.GET.get("document_number", "").strip()
    if doc_number:
        documents = documents.filter(document_number__icontains=doc_number)
    documents = documents.order_by("name")  # or another order as needed

    # sort documents by id then vessel
    documents = sorted(
        documents, key=lambda x: (x.id, x.vessel.name if x.vessel else "")
    )

    context = {
        "documents": documents,
        "vessels": Vessel.objects.all(),
        "selected_vessels": selected_vessels,
    }

    return render(request, "documents.html", context)


def document_detail(request, document_id):
    """
    Render the document detail page.
    Displays information about a specific document, including its pages and
    associated detections if they have been created.
    """

    document = Document.objects.get(id=document_id)
    pages = Page.objects.filter(document=document).order_by("page_number")

    rendered_detections = {}

    for p in pages:
        detections = Detection.objects.filter(page=p).order_by("created_at")
        det_tuple = (p.page_number, detections)
        rendered_detections[p] = rendered_detections.get(p, []).extend(
            det_tuple
        )

    context = {
        "document": document,
        "pages": pages,
    }

    return render(request, "document_detail.html", context)


def delete_documents_from_vessel(request):
    """
    Render the form for deleting documents from a vessel.
    This form allows users to select a vessel and delete all documents
    associated with that vessel.
    """

    if request.method == "POST":
        form = DeleteDocumentsFromVesselForm(request.POST)
        if form.is_valid():
            vessel_id = form.cleaned_data["vessel"]
            vessel = Vessel.objects.get(id=vessel_id)
            documents = Document.objects.filter(vessel=vessel)

            # Delete all documents associated with the selected vessel
            documents.delete()

            # Redirect to the documents page after deletion
            return redirect("/ocr/documents")
    else:
        form = DeleteDocumentsFromVesselForm()

    return render(request, "delete_documents_from_vessel.html", {"form": form})

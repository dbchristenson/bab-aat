import logging

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render

from ocr.forms import DeleteDocumentsFromVesselForm, UploadFileForm
from ocr.main.intake.handle_upload import handle_uploaded_file
from ocr.main.utils.draw_detections import draw_detections
from ocr.main.utils.loggers import basic_logging
from ocr.models import Detection, Document, Page, Truth, Vessel

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
            vessel_name = form.cleaned_data["vessel"]
            file = form.cleaned_data["file"]

            try:
                handle_uploaded_file(file, vessel_name)
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
    vessels_qs = Vessel.objects.all()
    selected_vessel_names = list(
        vessels_qs.filter(id__in=selected_vessels).values_list(
            "name", flat=True
        )
    )
    documents = Document.objects.all()
    if selected_vessels:
        documents = documents.filter(vessel__id__in=selected_vessels)
    doc_number = request.GET.get("document_number", "").strip()
    if doc_number:
        documents = documents.filter(document_number__icontains=doc_number)

    sort_key = request.GET.get("sort", "id")  # 'id' or 'file_size'
    order = request.GET.get("order", "asc")  # 'asc' or 'desc'
    field_map = {
        "id": "id",
        "file_size": "file_size",
    }
    django_field = field_map.get(sort_key, "id")
    prefix = "" if order == "asc" else "-"
    documents = documents.order_by(f"{prefix}{django_field}")

    # --- pagination (50 per page) ---
    paginator = Paginator(documents, 50)
    page_num = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_num)

    # Build a slim “1, …, current–1, current, current+1, …, last” list
    total = paginator.num_pages
    current = page_obj.number
    pages = [1]

    if current > 3:
        pages.append("…")

    for p in (current - 1, current, current + 1):
        if 1 < p < total:
            pages.append(p)

    if current < total - 2:
        pages.append("…")

    if total > 1:
        pages.append(total)

    context = {
        "documents": documents,
        "page_obj": page_obj,
        "page_numbers": pages,
        "vessels": vessels_qs,
        "selected_vessels": selected_vessels,
        "selected_vessel_names": selected_vessel_names,
        "sort": sort_key,
        "order": order,
        "base_query": "&".join(
            f"{k}={v}" for k, v in request.GET.items() if k not in ["page"]
        ),
    }

    return render(request, "documents.html", context)


def document_detail(request, document_id):
    """
    Render the document detail page.
    Displays information about a specific document, including its pages and
    associated detections if they have been created.
    """
    # Get the config from the request, default to "production.json"
    # This config is used to filter detections based on the configuration
    # used during the detection process.
    config = request.GET.get("config", None)
    if config is None:
        config = "production.json"

    document = Document.objects.get(id=document_id)
    pages = Page.objects.filter(document=document).order_by("page_number")

    page_detections = []
    for p in pages:
        dets = Detection.objects.filter(page=p, config=config)
        page_detections.append((p, dets))

    associated_truths = Truth.objects.filter(
        document_number=document.document_number
    )
    if associated_truths.exists():
        truths = associated_truths.values_list("text", flat=True)
    else:
        truths = None

    # Get all configs for the current document
    # This is used to populate the dropdown for
    # selecting different configurations.
    configs = set()
    for p in pages:
        dets = Detection.objects.filter(page=p)
        for d in dets:
            configs.add(d.config)

    context = {
        "document": document,
        "page_detections": page_detections,
        "config": config,
        "configs": configs,
        "truths": truths,
        "vessel": document.vessel.name if document.vessel else None,
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
            vessel_name = form.cleaned_data["vessel"]
            vessel = Vessel.objects.get(name=vessel_name)
            documents = Document.objects.filter(vessel=vessel)

            # Delete all documents associated with the selected vessel
            documents.delete()

            # Redirect to the documents page after deletion
            return redirect("/ocr/documents")
    else:
        form = DeleteDocumentsFromVesselForm()

    return render(request, "delete_documents_from_vessel.html", {"form": form})

from pathlib import Path

import markdown
from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from loguru import logger

from ocr.forms import (
    DeleteDocumentsFromVesselForm,
    DetectByOriginForm,
    OCRConfigForm,
    UploadFileForm,
)
from ocr.main.inference.handle_batch_detections import (
    handle_batch_document_detections,
)
from ocr.main.intake.handle_upload import handle_uploaded_file
from ocr.models import Detection, Document, OCRConfig, Page, Vessel
from ocr.tasks import draw_ocr_results as draw_ocr_results_task
from ocr.tasks import get_document_detections as get_document_detections_task


def index(request):
    """
    Render the index page with documentation from markdown file.
    """
    context = {
        "markdown_content": "",
        "markdown_error": None,
        "toc": None,
        "expected_path": None,
    }

    MARKDOWN_AVAILABLE = True
    if not MARKDOWN_AVAILABLE:
        context["markdown_error"] = (
            "Markdown library not installed. Please run: pip install markdown"
        )
        context["expected_path"] = "pip install markdown"
        return render(request, "index.html", context)

    # Look for documentation files in order of preference
    doc_paths = [
        Path(settings.BASE_DIR) / "README.md",
        Path(settings.BASE_DIR) / "docs" / "README.md",
        Path(settings.BASE_DIR) / "docs" / "index.md",
        Path(settings.BASE_DIR) / "DOCUMENTATION.md",
        Path(settings.BASE_DIR) / "ocr" / "docs" / "README.md",
    ]

    markdown_file = None
    for path in doc_paths:
        if path.exists():
            markdown_file = path
            break

    if markdown_file:
        try:
            # Configure markdown with extensions
            md = markdown.Markdown(
                extensions=[
                    "toc",
                    "fenced_code",
                    "tables",
                    "codehilite",
                    "attr_list",
                ],
                extension_configs={
                    "toc": {
                        "permalink": True,
                        "permalink_class": "header-link",
                        "permalink_title": "Link to this section",
                    },
                    "codehilite": {
                        "css_class": "highlight",
                        "use_pygments": False,
                    },
                },
            )

            # Read and convert markdown
            with open(markdown_file, "r", encoding="utf-8") as f:
                markdown_text = f.read()

            # Convert to HTML
            html_content = md.convert(markdown_text)

            context.update(
                {
                    "markdown_content": html_content,
                    "toc": md.toc if hasattr(md, "toc") and md.toc else None,
                }
            )

            logger.info(
                f"Successfully loaded documentation from {markdown_file}"
            )

        except Exception as e:
            logger.error(f"Error reading markdown file {markdown_file}: {e}")
            context["markdown_error"] = (
                f"Error reading documentation file: {str(e)}"
            )
            context["expected_path"] = str(markdown_file)
    else:
        context["markdown_error"] = "No documentation file found"
        context["expected_path"] = " or ".join(str(p) for p in doc_paths)
        logger.warning(
            "No documentation markdown file found in expected locations"
        )

    return render(request, "index.html", context)


# UPLOAD
# ------------------------------------------------------------------------------
def upload(request):
    """
    Render the upload page. Here users can upload individual pdf documents
    or compressed zip files for processing. Processing involves extracting
    data from the documents and storing it in a database.
    """

    if request.method == "POST":
        logger.info("Received a POST request for file upload.")
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            logger.info("Form is valid. Processing file upload.")
            vessel = form.cleaned_data["vessel"]
            vessel_id = vessel.id if vessel else None
            file = form.cleaned_data["file"]

            try:
                handle_uploaded_file(file, vessel_id)
            except Exception as e:
                logger.error(f"Error processing file: {e}")
                return render(request, "upload.html", {"form": form})

            return render(request, "upload_success.html")
        else:
            logger.error("Form is invalid.")
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


# DOCUMENTS
# ------------------------------------------------------------------------------
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
        )  # noqa E501
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
    selected_config_id = request.GET.get("config_id", None)
    all_configs = OCRConfig.objects.all().order_by("name")
    selected_config = None

    if selected_config_id:
        try:
            selected_config = OCRConfig.objects.get(id=selected_config_id)
        except OCRConfig.DoesNotExist:
            logger.warning(f"Config with id {selected_config_id} not found.")
            # Optionally, fall back to the first config or no config
            if all_configs.exists():
                selected_config = all_configs.first()
    elif all_configs.exists():
        selected_config = all_configs.first()

    document = get_object_or_404(Document, id=document_id)
    pages = Page.objects.filter(document=document).order_by("page_number")

    page_detections = []
    if selected_config:
        for p in pages:
            dets = Detection.objects.filter(page=p, config=selected_config)
            page_detections.append((p, dets)) if dets.exists() else None

            if not dets.exists():
                logger.info(
                    f"No detections found for document {document_id}, "
                    f"page {p.page_number}, config {selected_config.name}"
                )
    else:
        logger.warning("No OCRConfig selected, no detections will be shown.")

    # check if page_detections
    draw_ocr = bool(page_detections)

    context = {
        "document": document,
        "page_detections": page_detections,
        "configs": all_configs,
        "selected_config": selected_config,
        "draw_ocr": draw_ocr,
        "vessel": document.vessel.name if document.vessel else None,
    }

    logger.info(context)
    return render(request, "document_detail.html", context)


def trigger_document_detections(request, document_id):
    """
    Trigger OCR detection for a specific document using a selected OCR config.
    This function handles the POST request to start the OCR task for the
    specified document and config. It deletes any existing detections for
    the document and config before starting the new OCR task.
    """
    if request.method == "POST":
        config_id = request.POST.get("config_id")
        if not config_id:
            return redirect(
                reverse("ocr:document_detail", args=[document_id])
            )  # noqa E501

        try:
            # Ensure document and config exist
            document = get_object_or_404(Document, id=document_id)
            config = get_object_or_404(OCRConfig, id=config_id)

            # Delete existing detections for this document and config
            # Get all page IDs for the document
            page_ids = Page.objects.filter(document=document).values_list(
                "id", flat=True
            )
            Detection.objects.filter(
                page_id__in=page_ids, config=config
            ).delete()
            logger.info(
                f"Deleted existing detections for document {document.id} and config {config.name}"  # noqa E501
            )

            get_document_detections_task.delay(document.id, config.id)
            logger.info(
                f"Triggered OCR task for document {document_id} with config {config_id}"  # noqa E501
            )
        except Exception as e:
            logger.error(f"Error triggering OCR task: {e}")

        return redirect(
            reverse("ocr:document_detail", args=[document_id])
            + f"?config_id={config_id}"
        )
    # Should not be reached via GET, or handle appropriately
    return redirect(reverse("ocr:document_detail", args=[document_id]))


def trigger_draw_ocr(request, document_id):
    """
    Trigger the drawing of OCR results for a specific document.
    This function handles the POST request to draw OCR results on the
    specified document's pages.

    Args:
        request: The HTTP request object.
        document_id: The ID of the document to draw OCR results on.
        config_id: The ID of the OCRConfig to use for drawing.

    Returns:
        Redirects to a new URL with the rendered bounding boxes of the
        OCR results on the document's pages.
    """
    if request.method == "POST":
        config_id = request.POST.get("config_id")

        try:
            draw_ocr_results_task.delay(document_id, config_id)

            logger.info(
                f"Drawing OCR results for document {document_id} with config {config_id}"  # noqa E501
            )

            return redirect(
                reverse(
                    "ocr:documenet_detail",
                    args=[document_id] + f"?config_id={config_id}",
                )  # noqa E501
            )
        except Exception as e:
            logger.error(f"Error triggering draw OCR: {e}")

        return redirect(
            reverse("ocr:document_detail", args=[document_id])
            + f"?config_id={config_id}"
        )
    # Should not be reached via GET, or handle appropriately
    return redirect(reverse("ocr:document_detail", args=[document_id]))


# DELETE
# ------------------------------------------------------------------------------
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


# OCR CONFIG
# ------------------------------------------------------------------------------
def create_ocr_config(request):
    if request.method == "POST":
        form = OCRConfigForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("ocr:documents")
    else:
        form = OCRConfigForm()
    return render(request, "create_ocr_config.html", {"form": form})


# DETECT
# ------------------------------------------------------------------------------
def detect_by_origin(request):
    """
    Render the form for selecting a department origin for document detection.

    This form allows users to select a department origin from a list
    of available origins. When submitted, it will trigger the detection
    process for documents associated with the selected origin.

    Query Parameters:
        vessel: (optional) Vessel id to filter on.
        department_origin: (optional) Department origin to filter on.
    """
    show_no_documents_modal = False
    if request.method == "POST":
        form = DetectByOriginForm(request.POST)
        if form.is_valid():
            logger.info("Batch detection form is valid.")
            vessel = form.cleaned_data["vessel"]
            department_origin = form.cleaned_data["department_origin"]
            config = form.cleaned_data["config"]
            logger.info(
                f"Selected vessel: {vessel.name}, "
                f"origin: {department_origin}, "
                f"config: {config.name}"
            )
            task_results = handle_batch_document_detections(
                vessel_id=vessel.id,
                department_origin=department_origin,
                config_id=config.id,
            )

            if not task_results:
                show_no_documents_modal = True
            elif isinstance(task_results, list) and not task_results:
                pass
            else:
                return redirect("ocr:detect_success")
    else:
        form = DetectByOriginForm()

    return render(
        request,
        "detect_by_origin.html",
        {"form": form, "show_no_documents_modal": show_no_documents_modal},
    )


def detect_success(request):
    """
    Render the detection success page.
    """
    return render(request, "detect_success.html")

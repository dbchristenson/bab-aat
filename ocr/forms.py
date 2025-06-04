import json

import magic
from django import forms
from django.core.validators import FileExtensionValidator
from loguru import logger

from ocr.models import Document, OCRConfig, Vessel


class UploadFileForm(forms.Form):
    """
    Form for uploading files. The form allows users to upload either a PDF
    document or a ZIP file containing multiple PDF documents.
    """

    vessel = forms.ModelChoiceField(
        queryset=Vessel.objects.all(),
        empty_label="— select vessel —",
        required=True,
        help_text="Select the vessel associated with these documents",
    )

    file = forms.FileField(
        label="Select a file",
        help_text="File can be a PDF document or a ZIP file containing multiple PDF documents.",  # noqa 501
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf", "zip"]),
        ],
        max_length=100,
        required=True,
        widget=forms.ClearableFileInput(
            attrs={"id": "id_file", "multiple": False}
        ),
    )

    def clean_file(self):
        # File validation
        file = self.cleaned_data.get("file")
        if not file:
            raise forms.ValidationError(
                "No file selected. Please select a file."
            )

        # File size
        max_size = 2.5 * 1024 * 1024 * 1024  # 2.5 GB in bytes
        if file.size > max_size:
            logger.error("File size exceeds 2.5 GB limit.")
            raise forms.ValidationError("File size exceeds 2.5 GB limit.")

        # File type validation
        allowed_exts = ["pdf", "zip"]
        allowed_mime_types = [
            "application/pdf",
            "application/zip",
            "application/x-zip-compressed",
        ]

        ext = file.name.split(".")[-1].lower()
        if ext not in allowed_exts:
            logger.error(
                f"Invalid file extension: {ext}. Allowed: {allowed_exts}"
            )
            raise forms.ValidationError(
                "Invalid file type. Only PDF and ZIP files are allowed."
            )

        mime_type = magic.from_buffer(file.read(2048), mime=True)
        file.seek(0)  # Reset file pointer to the beginning after reading

        if mime_type not in allowed_mime_types:
            logger.error(
                f"Invalid MIME type: {mime_type}. Allowed: {allowed_mime_types}"  # noqa 501
            )
            raise forms.ValidationError(
                "Invalid file type. Only PDF and ZIP files are allowed."
            )

        return file


class DeleteDocumentsFromVesselForm(forms.Form):
    """
    Form for deleting a document from a vessel.
    This form allows users to select a document from a list of documents
    associated with a specific vessel and delete it. The form is rendered
    as a dropdown list of vessels. When submitted, it will delete all
    documents associated with the selected vessel.
    """

    vessel = forms.ModelChoiceField(
        queryset=Vessel.objects.all(),
        empty_label="— select vessel —",
        required=True,
        help_text="Select the vessel associated with these documents",
    )


class OCRConfigForm(forms.ModelForm):
    class Meta:
        model = OCRConfig
        fields = ["name", "config"]
        widgets = {
            "config": forms.Textarea(
                attrs={
                    "rows": 10,
                    "cols": 80,
                    "placeholder": "Enter JSON config here",
                }
            ),
        }

    def clean_config(self):
        config_data = self.cleaned_data["config"]
        try:
            if isinstance(config_data, str):
                json.loads(config_data)
            elif not isinstance(config_data, dict):
                raise forms.ValidationError(
                    "Config must be a valid JSON string or a dictionary."
                )
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format.")
        # The model field will store it as a Python dict.
        return config_data


class DetectByOriginForm(forms.Form):
    """
    Form for selecting a department origin for document detection.
    This form allows users to select a department origin from a list
    of available origins. When submitted, it will trigger the detection
    process for documents associated with the selected origin.
    """

    vessel = forms.ModelChoiceField(
        queryset=Vessel.objects.all(),
        empty_label="— select vessel —",
        required=True,
        help_text="Select the vessel associated with the documents to detect",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get distinct department_origin values from the Document model
        # and format them for the ChoiceField.
        distinct_origins = (
            Document.objects.filter(department_origin__isnull=False)
            .values_list("department_origin", flat=True)
            .distinct()
            .order_by("department_origin")
        )
        origin_choices = [("", "— select department origin —")] + [
            (origin, origin) for origin in distinct_origins
        ]
        self.fields["department_origin"].choices = origin_choices

    department_origin = forms.ChoiceField(
        # Choices will be set in __init__
        choices=[],
        required=True,
        help_text="Select the department origin of the documents to detect",
    )

    config = forms.ModelChoiceField(
        queryset=OCRConfig.objects.all(),
        empty_label="— select OCR config —",
        required=True,
        help_text="Select the OCR configuration to use for detection",
    )

    only_without_detections = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Only detect documents without existing detections",
    )


class ProcessDetectionsFormByUnprocessed(forms.Form):
    """
    Form for processing detections by unprocessed documents.
    This form allows users to select a vessel and a specific OCR config
    to process detections for documents that have not been processed yet.

    The processed detections will be turned into tags and saved.
    """

    vessel = forms.ModelChoiceField(
        queryset=Vessel.objects.all(),
        empty_label="— select vessel —",
        required=True,
        help_text="Select the vessel associated with the documents to process",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get distinct department_origin values from the Document model
        # and format them for the ChoiceField.
        distinct_origins = (
            Document.objects.filter(department_origin__isnull=False)
            .values_list("department_origin", flat=True)
            .distinct()
            .order_by("department_origin")
        )
        origin_choices = [("", "— select department origin —")] + [
            (origin, origin) for origin in distinct_origins
        ]
        self.fields["origin"].choices = origin_choices

    origin = forms.ChoiceField(
        choices=[],
        required=False,
        help_text="Select the department origin of the documents to process",
    )
    config = forms.ModelChoiceField(
        queryset=OCRConfig.objects.all(),
        empty_label="— select OCR config —",
        required=True,
        help_text="Select the OCR configuration to use for processing",
    )
    only_without_tags = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Only process documents without existing tags",
    )


class ExportForm(forms.Form):
    """
    Form for exporting document(s) data to Excel.

    The structure of the Excel file will be a denormalized table that
    focuses on relaying information about the tags of the documents.
    The table will include the following columns:
        - Document ID
        - Document Number
        - Page Number
        - Tag Text
        - Location (Bounding Box Coordinates)
        - Equipment Tag (Prediction for if tag is an equipment tag)
        - Created At (Timestamp of when the tag was created)
    """

    document = forms.ModelChoiceField(
        queryset=Document.objects.all(),
        empty_label="— select document —",
        required=False,
        help_text="Select a document to export, leave blank to query",
    )
    vessel = forms.ModelChoiceField(
        queryset=Vessel.objects.all(),
        empty_label="— select vessel —",
        required=True,
        help_text="Select the vessel associated with the documents to export",
    )
    department_origin = forms.ChoiceField(
        choices=[],
        required=False,
        help_text="Select the department origin of the documents to export",
    )
    config = forms.ModelChoiceField(
        queryset=OCRConfig.objects.all(),
        empty_label="— select OCR config —",
        required=True,
        help_text="Select the OCR configuration to filter documents by",
    )
    export_type = forms.ChoiceField(
        choices=["excel", "pdf"],
        initial="excel",
        required=True,
        help_text="Select the type of file to export to",
    )

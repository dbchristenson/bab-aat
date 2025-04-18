import logging

import magic
from django import forms
from django.core.validators import FileExtensionValidator

from ocr.main.utils.loggers import basic_logging
from ocr.models import Vessel

basic_logging(__name__)


class UploadFileForm(forms.Form):
    """
    Form for uploading files. The form allows users to upload either a PDF
    document or a ZIP file containing multiple PDF documents.
    """

    vessels = Vessel.objects.all()
    vessel_choices = [(vessel.id, vessel.name) for vessel in vessels]
    vessel_choices.sort(key=lambda x: x[1])
    vessel_choices.insert(0, ("", "Select a vessel"))

    vessel = forms.ChoiceField(
        choices=vessel_choices,
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "aria-label": "Select a vessel",
            }
        ),
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
            logging.error("File size exceeds 2.5 GB limit.")
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
            logging.error(
                f"Invalid file extension: {ext}. Allowed: {allowed_exts}"
            )
            raise forms.ValidationError(
                "Invalid file type. Only PDF and ZIP files are allowed."
            )

        mime_type = magic.from_buffer(file.read(2048), mime=True)
        file.seek(0)  # Reset file pointer to the beginning after reading

        if mime_type not in allowed_mime_types:
            logging.error(
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

    vessels = Vessel.objects.all()
    vessel_choices = [(vessel.id, vessel.name) for vessel in vessels]
    vessel_choices.sort(key=lambda x: x[1])
    vessel_choices.insert(0, ("", "Select a vessel"))

    vessel = forms.ChoiceField(
        choices=vessel_choices,
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "aria-label": "Select a vessel",
            }
        ),
        help_text="Select the vessel associated with these documents",
    )

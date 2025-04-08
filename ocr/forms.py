from django import forms
from django.core.validators import FileExtensionValidator, MaxValueValidator

from ocr.models import Vessel


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
            MaxValueValidator(50 * 1024 * 1024),  # 50 MB
        ],
        max_length=100,
        required=True,
        widget=forms.ClearableFileInput(attrs={"multiple": False}),
    )

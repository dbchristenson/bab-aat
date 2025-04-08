from django import forms


class UploadFileForm(forms.Form):
    """
    Form for uploading files. The form allows users to upload either a PDF
    document or a ZIP file containing multiple PDF documents.
    """

    file = forms.FileField(
        label="Select a file",
        help_text="File can be a PDF document or a ZIP file containing multiple PDF documents.",  # noqa 501
        required=True,
        widget=forms.ClearableFileInput(attrs={"multiple": False}),
    )

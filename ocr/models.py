from django.db import models


# Create your models here.
class Document(models.Model):
    """
    A document is a collection of pages representing engineering documents.

    Params:
        name (str): The name of the document.
        document_number (str): The document number.
        file_path (str): The path to the document file.
        file_size (int): The size of the document file in bytes.
        last_modified (datetime): The last modified date of the document.
        created_at (datetime): The date when the document was created.
    """

    name = models.CharField(max_length=255)
    document_number = models.CharField(max_length=255, null=True)
    file_path = models.CharField(max_length=255)
    file_size = models.IntegerField()  # in bytes
    last_modified = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Page(models.Model):
    """
    A page is an image of a document. Page numbers are 0-indexed.

    Params:
        document (Document): The document to which this page belongs.
        page_number (int): The page number of the document (0-indexed).
        img_path (str): The path to the image file of the page.
        created_at (datetime): The date when the page was created.
    """

    document = models.ForeignKey(
        Document, related_name="pages", on_delete=models.CASCADE
    )
    page_number = models.IntegerField()  # 0-indexed
    img_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.name} - Page {self.page_number}"


class Detection(models.Model):
    """
    A detection is a recognized text block on a page.

    Params:
        page (Page): The page on which the detection was made.
        text (str): The recognized text.
        confidence (float): The confidence score of the detection.
        created_at (datetime): The date when the detection was created.
    """

    page = models.ForeignKey(
        Page, related_name="detections", on_delete=models.CASCADE
    )
    text = models.CharField(max_length=255)
    confidence = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.page.document.name} - Page {self.page.page_number} - {self.text}"  # noqa E501


class Truth(models.Model):
    """
    A truth is a manually annotated text block on a page. We will use
    truths to evaluate the performance of the OCR engine.

    Params:
        document (Document): The document to which this truth belongs.
        text (str): The annotated text.
        created_at (datetime): The date when the truth was created.
    """

    document = models.ForeignKey(
        Document, related_name="truths", on_delete=models.CASCADE
    )
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.name} - {self.text}"

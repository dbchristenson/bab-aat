from django.db import models


# Create your models here.
class Vessel(models.Model):
    """
    A vessel is a ship or boat that is associated with a document.
    Each vessel has a unique name. These are changed manually as new
    vessels are not commonly added.
    Params:
        name (str): The name of the vessel.
        created_at (datetime): The date when the vessel was created.
    """

    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Document(models.Model):
    """
    A document is a collection of pages representing engineering documents.

    Params:
        name (str): The name of the document.
        vessel (str): The name of the vessel associated with the document, optional.    # noqa E501
        document_number (str): The document number.
        file_path (str): The path to the document file.
        file_size (int): The size of the document file in bytes.
        last_modified (datetime): The last modified date of the document.
        created_at (datetime): The date when the document was created.
    """

    name = models.CharField(max_length=255)
    vessel = models.ForeignKey(
        Vessel, related_name="documents", on_delete=models.CASCADE, null=True
    )
    document_number = models.CharField(max_length=255, null=True)
    file = models.FileField(upload_to="documents/")
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
        created_at (datetime): The date when the page was created.
    """

    document = models.ForeignKey(
        Document, related_name="pages", on_delete=models.CASCADE
    )
    page_number = models.IntegerField()  # 0-indexed
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.name} - Page {self.page_number}"


class Detection(models.Model):
    """
    A detection is a recognized text block on a page.

    Params:
        page (Page): The page on which the detection was made.
        text (str): The recognized text.
        bbox (list): The bounding box coordinates of the detected text.
        confidence (float): The confidence score of the detection.
        experiment (str): The name of the experiment or model used.
        created_at (datetime): The date when the detection was created.
    """

    page = models.ForeignKey(
        Page, related_name="detections", on_delete=models.CASCADE
    )
    text = models.CharField(max_length=255)
    bbox = models.JSONField()  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    confidence = models.FloatField()
    config = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.page.document.name} - Page {self.page.page_number} - {self.text}"  # noqa E501


class Tag(models.Model):
    """
    A tag can be made up of one or more detections. Tags are complete text
    blocks that signify greater importance than a single detection might. For
    example, two detections arranged above and below each other might be a
    single tag. Tags are algorithmically determined and may still contain
    errors.

    We denormalize the db to add page_number because some documents have 100+
    pages in them. In the event of storage failure where we lose page data,
    we can still recover the page number from the tag and the document.

    Params:
        document (Document): The document to which this tag belongs.
        page_number (int): The page number of the document (0-indexed).
        text (str): The text of the tag.
        bbox (list): The bounding box coordinates of the merged shape.
        algorithm (str): The algorithm used to create the tag.
        detections (list): The raw OCR lines used to build this tag.
        confidence (float): Minimum confidence of the detections used.
        created_at (datetime): The date when the tag was created.
    """

    document = models.ForeignKey(
        Document, related_name="tags", on_delete=models.CASCADE, null=True
    )
    page_number = models.IntegerField()  # 0-indexed
    text = models.CharField(max_length=255)
    bbox = models.JSONField(
        help_text="Polygon coords [[x1,y1],…] of the merged shape"
    )
    algorithm = models.CharField(
        max_length=100,
        null=True,
        help_text="e.g. 'circle_hough', 'dbscan', 'proximity_merge'",
    )
    detections = models.ManyToManyField(
        Detection,
        related_name="tags",
        help_text="Raw OCR lines used to build this tag",
    )
    confidence = models.FloatField(
        null=True,
        help_text="Minimum confidence of the detections used in this tag",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.name} - {self.text}"


class Truth(models.Model):
    """
    A truth is a manually annotated text block on a page. We will use
    truths to evaluate the performance of the OCR engine.

    Params:
        document (Document): The document to which this truth belongs.
        text (str): The annotated text.
        created_at (datetime): The date when the truth was created.
    """

    document_number = models.CharField(max_length=255)
    document = models.ForeignKey(
        Document, related_name="truths", on_delete=models.CASCADE, null=True
    )
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.name} - {self.text}"

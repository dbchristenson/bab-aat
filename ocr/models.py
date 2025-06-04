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
        department_origin (str): The department origin of the document.
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
    department_origin = models.CharField(max_length=10, blank=True)
    file = models.FileField(upload_to="documents/")
    file_size = models.IntegerField()  # in bytes
    last_modified = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def _get_department_origin(self):
        """
        Returns the department origin of the document.
        """
        if not self.document_number:
            return ""

        return self.document_number.split("-")[1].strip().upper()

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Override the save method to set the department_origin field
        based on the document_number.
        """
        if not self.department_origin and self.document_number:
            self.department_origin = self._get_department_origin()
        super().save(*args, **kwargs)


class Page(models.Model):
    """
    A page is an image of a document. Page numbers are 1-indexed.

    Params:
        document (Document): The document to which this page belongs.
        page_number (int): The page number of the document (1-indexed).
        created_at (datetime): The date when the page was created.
        annotated_images (JSON): Dict storing annotated image paths per config.
    """

    document = models.ForeignKey(
        Document, related_name="pages", on_delete=models.CASCADE
    )
    page_number = models.IntegerField()  # 1-indexed
    created_at = models.DateTimeField(auto_now_add=True)
    annotated_images = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.document.name} - Page {self.page_number}"

    def get_annotated_image_url(self, config_id):
        """Get the URL for the annotated image for a specific config."""
        from django.conf import settings

        image_path = self.annotated_images.get(str(config_id))
        if image_path:
            return f"{settings.MEDIA_URL}{image_path}"
        return None

    def delete_annotated_image(self, config_id):
        """
        Delete the annotated image for a specific config.
        This method removes the image from the database and filesystem.
        """
        import os

        from django.conf import settings

        image_path = self.annotated_images.get(str(config_id))
        if image_path:
            full_path = os.path.join(settings.MEDIA_ROOT, image_path)
            if os.path.exists(full_path):
                os.remove(full_path)
            del self.annotated_images[str(config_id)]
            self.save()


class OCRConfig(models.Model):
    """
    Configuration parameters for the OCR engine.

    Params:
        name (str): The name of the configuration.
        config (JSON): The configuration parameters in JSON format.
        created_at (datetime): The date when the configuration was created.
    """

    name = models.CharField(max_length=255)
    config = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


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
    page_number = models.IntegerField()  # 1-indexed
    text = models.CharField(max_length=255)
    bbox = models.JSONField(
        help_text="Polygon coords [[x1,y1],…] of the merged shape"
    )
    algorithm = models.CharField(
        max_length=100,
        null=True,
        help_text="e.g. 'circle_hough', 'dbscan', 'proximity_merge'",
    )
    confidence = models.FloatField(
        null=True,
        help_text="Minimum confidence of the detections used in this tag",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    equipment_tag = models.BooleanField(default=False, null=True)

    def __str__(self):
        return f"{self.document.name} - {self.text}"

    def resolve_is_equipment_tag(self):
        """
        Check Tag text to determine if it is an equipment tag.
        If it is an equipment tag, set the equipment_tag field to True.

        A Tag is an equipment tag if it contains at least one letter,
        at least one number, and at least one hyphen.
        """
        import re

        if (
            re.search(r"[A-Za-z]", self.text)
            and re.search(r"\d", self.text)
            and re.search(r"-", self.text)
        ):
            self.equipment_tag = True
        else:
            self.equipment_tag = False


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
    config = models.ForeignKey(OCRConfig, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tag = models.ForeignKey(
        Tag, related_name="detections", on_delete=models.SET_NULL, null=True
    )

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

    document_number = models.CharField(max_length=255)
    document = models.ForeignKey(
        Document, related_name="truths", on_delete=models.CASCADE, null=True
    )
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.name} - {self.text}"

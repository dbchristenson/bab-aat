import datetime as dt

from peewee import (
    CharField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
)

db = SqliteDatabase("main.db")


class BaseModel(Model):
    class Meta:
        database = db


class Document(BaseModel):
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

    name = CharField()
    document_number = CharField(null=True)
    file_path = CharField()
    file_size = IntegerField()  # in bytes
    last_modified = DateTimeField()
    created_at = DateTimeField(default=dt.datetime.now)

    class Meta:
        database = db


class Page(BaseModel):
    """
    A page is an image of a document. Page numbers are 0-indexed.

    Params:
        document (Document): The document to which this page belongs.
        page_number (int): The page number of the document (0-indexed).
        img_path (str): The path to the image file of the page.
        created_at (datetime): The date when the page was created.
    """

    document = ForeignKeyField(Document, backref="pages", on_delete="CASCADE")
    page_number = IntegerField()  # 0-indexed
    img_path = CharField()
    created_at = DateTimeField(default=dt.datetime.now)

    class Meta:
        database = db


class Detection(BaseModel):
    """
    A detection is an object detected in an image.

    Params:
        document (Document): The document to which this detection belongs.
        page (Page): The page to which this detection belongs.
        ocr_text (str): The text extracted from the image using OCR.
        x_center (float): The x-coordinate of the center of the bounding box.
        y_center (float): The y-coordinate of the center of the bounding box.
        width (float): The width of the bounding box.
        height (float): The height of the bounding box.
        confidence (float): The confidence score of the detection.
        cropped_img_path (str): The path to the cropped image of the detection.
        created_at (datetime): The date when the detection was created.
    """

    document = ForeignKeyField(
        Document, backref="detections", on_delete="CASCADE"
    )
    page = ForeignKeyField(Page, backref="detections", on_delete="CASCADE")
    ocr_text = CharField()
    x_center = FloatField(null=True)
    y_center = FloatField(null=True)
    width = FloatField(null=True)
    height = FloatField(null=True)
    confidence = FloatField(null=True)
    cropped_img_path = CharField(null=True)
    created_at = DateTimeField(default=dt.datetime.now)

    class Meta:
        database = db


db.connect()
db.create_tables([Document, Page, Detection])

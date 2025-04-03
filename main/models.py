import datetime as dt

from peewee import (CharField, DateTimeField, FloatField, ForeignKeyField,
                    IntegerField, Model, SqliteDatabase)

db = SqliteDatabase("main.db")


class BaseModel(Model):
    class Meta:
        database = db


class Document(BaseModel):
    """
    A document is a collection of pages representing engineering documents.
    """

    name = CharField()
    document_number = CharField()
    file_path = CharField()
    file_size = IntegerField()  # in bytes
    last_modified = DateTimeField()
    created_at = DateTimeField(default=dt.datetime.now)

    class Meta:
        database = db


class Page(BaseModel):
    """
    A page is an image of a document. Page numbers are 0-indexed.
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
    """

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

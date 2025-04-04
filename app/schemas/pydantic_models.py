from datetime import datetime

from pydantic import BaseModel

from main.models import Document, Page


class DocumentResponse(BaseModel):
    """
    Pydantic model for the Document response.
    This model is used to validate the data returned by the API.
    """

    name: str
    document_number: str | None = None
    file_path: str
    file_size: int  # in bytes
    last_modified: datetime
    created_at: datetime

    class Config:
        orm_mode = True


class PageResponse(BaseModel):
    """
    Pydantic model for the Page response.
    This model is used to validate the data returned by the API.
    """

    document: Document

    class Config:
        orm_mode = True


class DetectionResponse(BaseModel):
    """
    Pydantic model for the Detection response.
    This model is used to validate the data returned by the API.
    """

    class Config:
        orm_mode = True

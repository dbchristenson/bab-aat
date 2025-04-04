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
    page_number: int  # 0-indexed
    img_path: str
    created_at: datetime

    class Config:
        orm_mode = True


class DetectionResponse(BaseModel):
    """
    Pydantic model for the Detection response.
    This model is used to validate the data returned by the API.
    """

    document: Document
    page: Page
    ocr_text: str
    x_center: float
    y_center: float
    width: float
    height: float
    confidence: float
    cropped_img_path: str
    created_at: datetime

    class Config:
        orm_mode = True

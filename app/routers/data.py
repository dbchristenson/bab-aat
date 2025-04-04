import requests
from fastapi import APIRouter

from app.schemas.pydantic_models import (
    DetectionResponse,
    DocumentResponse,
    PageResponse,
)

router = APIRouter()


@router.get("/documents")
async def get_documents(limit: int = None):
    """
    Get all documents or a limited number of documents.
    If a limit is provided, return that many documents.
    """
    from main.models import Document

    documents = Document.select().execute()

    # TODO - Implement different queries

    if limit is not None:
        return documents[:limit]
    return documents


@router.get("/pages")
async def get_pages(limit: int = None):
    """
    Get all pages or a limited number of pages.
    If a limit is provided, return that many pages.
    """
    from main.models import Page

    pages = Page.select().execute()

    # TODO - Implement different queries

    if limit is not None:
        return pages[:limit]
    return pages


@router.get("/detections")
async def get_detections(limit: int = None):
    """
    Get all detections or a limited number of detections.
    If a limit is provided, return that many detections.
    """
    from main.models import Detection

    detections = Detection.select().execute()

    # TODO - Implement different queries

    if limit is not None:
        return detections[:limit]
    return detections


@router.get("/get/{document_number}", response_model=DocumentResponse)
async def get_document(document_number: str):
    """
    Get a document by its document number.
    """
    from main.models import Document

    doc = Document.get_or_none(Document.document_number == document_number)

    return {"document": doc}


@router.get("/get/{page_id}", response_model=PageResponse)
async def get_page(page_id: int):
    """
    Get a page by its ID.
    """
    from main.models import Page

    page = Page.get_or_none(Page.id == page_id)

    return {"page": page}


@router.get("/get/{detection_id}", response_model=DetectionResponse)
async def get_detection(detection_id: int):
    """
    Get a detection by its ID.
    """
    from main.models import Detection

    detection = Detection.get_or_none(Detection.id == detection_id)

    return {"detection": detection}


@router.get("/summary/{document_number}")
async def document_summary(document_number: str):
    """
    Get a summary of a document by its document number.
    """
    # Make a request to /get/{document_number} to get the document
    # and its pages
    response = requests.get(f"/get/{document_number}")
    if response.status_code != 200:
        return {"error": "Document not found"}

    return {"summary": response.json()}

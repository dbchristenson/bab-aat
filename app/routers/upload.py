from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

router = APIRouter()


@router.get("/")
async def serve_upload_page():
    """
    Serve the upload page.
    """
    # TODO - Implement the logic to serve the upload page
    # For now, we will just return a simple message
    return {"message": "Upload page"}


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file and return its filename and content type.
    """
    # Save the file to a temporary location or process it as needed
    # For now, we will just return the filename and content type
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(await file.read()),
    }

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import data, upload
from main.models import Detection, Document, Page
from main.utils.db_routing import db_manager
from main.utils.loggers import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI.
    """
    # logging setup
    setup_logging("ocr_api")  # Initialize logging system

    db_manager.connect(local=True)  # Connect to the local database

    try:
        db_manager.db.create_tables(
            [Document, Page, Detection], safe=True
        )  # Create tables if they don't exist
        logging.info("Database tables created or already exist.")

        yield

    except Exception as e:
        logging.error("Failed to init database: %s", e)

    # Disconnect from the database when the application stops
    finally:
        db_manager.close()


app = FastAPI(
    title="Bab-aat OCR API",
    description="API for OCR processing of engineering documents",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(data.router, prefix="/data", tags=["data"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])


@app.get("/")
async def root():
    return {"message": "Welcome to the Bab-aat OCR API!"}

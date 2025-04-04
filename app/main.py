from fastapi import FastAPI

from app.routers import data, upload


async def startup_event():
    """
    Startup event handler for FastAPI.
    This function is called when the application starts up.
    """
    # TODO - Initialize database connection or any other startup tasks
    pass


app = FastAPI(
    title="Bab-aat OCR API",
    description="API for OCR processing of engineering documents",
    version="0.1.0",
)

app.include_router(data.router, prefix="/data", tags=["data"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])


@app.get("/")
async def root():
    return {"message": "Welcome to the Bab-aat OCR API!"}

import os

from celery import shared_task
from django.core.files import File

from ocr.main.intake.handle_upload import handle_pdf
from ocr.models import Vessel


@shared_task(bind=True)
def process_pdf_task(self, disk_path: str, vessel_id: int, output_dir: str):
    """
    Celery task wrapper for handling pdfs
    """
    vessel = Vessel.objects.get(id=vessel_id)
    with open(disk_path, "rb") as f:
        django_file = File(f, name=os.path.basename(disk_path))
        handle_pdf(django_file, vessel, output_dir)

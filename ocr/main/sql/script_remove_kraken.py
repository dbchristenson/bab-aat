import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babaatsite.settings")
django.setup()

from ocr.models import Document, Vessel  # noqa E402


def remove_kraken() -> None:
    """
    This is a script which completely purges all Kraken documents from the
    database. This should also delete all associate pages and images for
    those documents as well as the documents themselves.
    It is not reversible and should be used with caution.
    """

    kraken_vessel_id = 1
    kraken_vessel = Vessel.objects.get(id=kraken_vessel_id)

    kraken_documents = Document.objects.filter(vessel=kraken_vessel)
    kraken_documents.delete()

    print("Deleted all Kraken documents from the database.")

    return True


remove_kraken()

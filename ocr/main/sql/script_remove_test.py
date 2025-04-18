import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babaatsite.settings")
django.setup()

from ocr.models import Document, Vessel  # noqa E402


def remove_test() -> None:
    """
    This is a script which completely purges all Test documents from the
    database. This should also delete all associate pages and images for
    those documents as well as the documents themselves.
    It is not reversible and should be used with caution.
    """

    test_vessel_id = 8
    vessel = Vessel.objects.get(id=test_vessel_id)

    documents = Document.objects.filter(vessel=vessel)
    documents.delete()

    print("Deleted all Test documents from the database.")

    return True


remove_test()

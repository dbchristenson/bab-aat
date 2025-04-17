from django.urls import path

from . import views

app_name = "ocr"

urlpatterns = [
    path("", views.index, name="index"),
    path("upload/", views.upload, name="upload"),
    path("upload_success/", views.upload_success, name="upload_success"),
    path("documents/", views.documents, name="documents"),
    path(
        "documents/<int:document_id>/",
        views.document_detail,
        name="document_detail",
    ),
    path(
        "documents/delete/from_vessel/",
        views.delete_documents_from_vessel,
        name="delete_documents_from_vessel",
    ),
]

from django.urls import path

from . import views

app_name = "ocr"

urlpatterns = [
    path("", views.index, name="index"),
    # upload
    path("upload/", views.upload, name="upload"),
    path("upload_success/", views.upload_success, name="upload_success"),
    # documents
    path("documents/", views.documents, name="documents"),
    path(
        "documents/<int:document_id>/",
        views.document_detail,
        name="document_detail",
    ),
    # delete
    path(
        "documents/delete_from_vessel/",
        views.delete_documents_from_vessel,
        name="delete_documents_from_vessel",
    ),
    # config
    path("configs/create/", views.create_ocr_config, name="create_ocr_config"),
    # detect
    path(
        "documents/<int:document_id>/get_detections/",
        views.trigger_document_detections,
        name="trigger_document_detections",
    ),
    path(
        "documents/detect_by_origin/",
        views.detect_by_origin,
        name="detect_by_origin",
    ),
]

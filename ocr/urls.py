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
        "documents/delete/from_vessel/",
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
        "documents/detect/by_origin/",
        views.detect_by_origin,
        name="detect_by_origin",
    ),
    path(
        "documents/detect/success/",
        views.detect_success,
        name="detect_success",
    ),
    # draw
    path(
        "documents/<int:document_id>/draw/",
        views.trigger_draw_ocr,
        name="trigger_draw_ocr",
    ),
    # dets -> tags
    path(
        "documents/process_detections/",
        views.process_detections,
        name="process_detections",
    ),
    # export
    path("documents/export/excel/", views.export_excel, name="export_excel"),
    path("documents/export/pdf/", views.export_pdf, name="export_pdf"),
]

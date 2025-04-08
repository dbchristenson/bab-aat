from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("upload/", views.upload, name="upload"),
    path("upload_success/", views.upload_success, name="upload_success"),
    path("documents/", views.documents, name="documents"),
]

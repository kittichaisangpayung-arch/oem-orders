from django.urls import path

from . import views

app_name = "ingestion"

urlpatterns = [
    path("upload/", views.upload_batch, name="upload"),
    path("batches/<int:batch_id>/preview/", views.batch_preview, name="batch_preview"),
    path("batches/<int:batch_id>/confirm/", views.confirm_batch, name="confirm_batch"),
    path("batches/<int:batch_id>/cancel/", views.cancel_batch, name="cancel_batch"),
    path("batches/<int:batch_id>/", views.batch_result, name="batch_result"),
    path("batches/<int:batch_id>/delete/", views.delete_batch, name="delete_batch"),
    path("batches/<int:batch_id>/manual/", views.manual_entry, name="manual_entry"),
    path("batches/<int:batch_id>/manual/save/", views.save_manual_po, name="save_manual_po"),
    path("batches/<int:batch_id>/manual/finish/", views.finish_manual_entry, name="finish_manual_entry"),
]

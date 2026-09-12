from django.urls import path

from . import views

app_name = "claims"

urlpatterns = [
    path("", views.claim_list_create, name="list_create"),
]

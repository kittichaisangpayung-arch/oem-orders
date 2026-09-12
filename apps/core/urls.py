from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("products/", views.product_config, name="product_config"),
]

from django.urls import path

from . import views

app_name = "manage_data"

urlpatterns = [
    path("customers/", views.CustomerListView.as_view(), name="customer_list"),
    path("customers/add/", views.CustomerCreateView.as_view(), name="customer_add"),
    path("customers/<int:pk>/edit/", views.CustomerUpdateView.as_view(), name="customer_edit"),
    path("customers/<int:pk>/delete/", views.CustomerDeleteView.as_view(), name="customer_delete"),

    path("stores/", views.StoreListView.as_view(), name="store_list"),
    path("stores/add/", views.StoreCreateView.as_view(), name="store_add"),
    path("stores/<int:pk>/edit/", views.StoreUpdateView.as_view(), name="store_edit"),
    path("stores/<int:pk>/delete/", views.StoreDeleteView.as_view(), name="store_delete"),

    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/add/", views.ProductCreateView.as_view(), name="product_add"),
    path("products/<int:pk>/edit/", views.ProductUpdateView.as_view(), name="product_edit"),
    path("products/<int:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),
]

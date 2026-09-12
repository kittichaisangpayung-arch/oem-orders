import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.core.models import Product


@pytest.mark.django_db
def test_product_config_updates_min_order_qty():
    user = User.objects.create_user(username="salesuser", password="testpass123")
    product = Product.objects.create(barcode="1234567890123", description="Test Product", min_order_qty=5)

    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("core:product_config"),
        {"product_id": product.pk, "min_order_qty": 20},
    )
    assert response.status_code == 302

    product.refresh_from_db()
    assert product.min_order_qty == 20


@pytest.mark.django_db
def test_product_config_get_lists_products():
    user = User.objects.create_user(username="viewer", password="testpass123")
    Product.objects.create(barcode="1234567890123", description="Test Product", min_order_qty=5)

    client = Client()
    client.force_login(user)

    response = client.get(reverse("core:product_config"))
    assert response.status_code == 200
    assert b"Test Product" in response.content

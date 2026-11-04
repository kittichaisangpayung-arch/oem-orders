import json

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.core.models import Customer, Product, Store
from apps.ingestion.models import PurchaseOrder, PurchaseOrderBatch


@pytest.mark.django_db
def test_missing_store_can_be_filled_manually_from_preview():
    user = User.objects.create_user(username="sales", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    with_po = Store.objects.create(customer=customer, store_code="S1", name="Store 1")
    missing = Store.objects.create(customer=customer, store_code="S2", name="Store 2")
    product = Product.objects.create(barcode="1234567890123", description="Cake")
    batch = PurchaseOrderBatch.objects.create(customer=customer)
    PurchaseOrder.objects.create(batch=batch, customer=customer, store=with_po, source_filename="a.pdf")

    client = Client()
    client.force_login(user)

    preview = client.get(reverse("ingestion:batch_preview", args=[batch.pk]))
    manual_url = f"{reverse('ingestion:manual_entry', args=[batch.pk])}?store={missing.pk}"
    assert manual_url in preview.content.decode()
    assert [s.pk for s in preview.context["missing_stores"]] == [missing.pk]

    page = client.get(manual_url)
    assert page.context["selected_store_id"] == str(missing.pk)
    assert f'<option value="{missing.pk}" selected>' in page.content.decode()

    response = client.post(
        reverse("ingestion:save_manual_po", args=[batch.pk]),
        json.dumps({"store_id": missing.pk, "line_items": [{"product_id": product.pk, "qty2": 4, "price": 10}]}),
        content_type="application/json",
    )
    assert response.json()["success"]

    preview = client.get(reverse("ingestion:batch_preview", args=[batch.pk]))
    assert list(preview.context["missing_stores"]) == []
    po = batch.purchase_orders.get(store=missing)
    assert po.entry_mode == PurchaseOrder.EntryMode.MANUAL
    assert list(po.line_items.values_list("qty2", flat=True)) == [4]


@pytest.mark.django_db
def test_finish_manual_entry_redirects_to_preview():
    user = User.objects.create_user(username="sales", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store 1")
    batch = PurchaseOrderBatch.objects.create(customer=customer)
    PurchaseOrder.objects.create(batch=batch, customer=customer, store=store)

    client = Client()
    client.force_login(user)
    response = client.post(reverse("ingestion:finish_manual_entry", args=[batch.pk]))
    assert response.json()["redirect_url"] == reverse("ingestion:batch_preview", args=[batch.pk])

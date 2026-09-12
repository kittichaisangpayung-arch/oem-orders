import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.claims.models import Claim
from apps.core.models import Customer, Product, Store
from apps.ingestion.models import POLineItem, PurchaseOrder, PurchaseOrderBatch


def _make_po_line(customer, store, product, qty2, unit_amount, batch, line_no=1):
    po = PurchaseOrder.objects.create(
        batch=batch,
        customer=customer,
        store=store,
        store_code_raw=store.store_code,
        store_name_raw=store.name,
        source_filename="test.pdf",
    )
    line_item = POLineItem.objects.create(
        purchase_order=po,
        product=product,
        barcode_raw=product.barcode,
        description_raw=product.description,
        qty=qty2,
        qty2=qty2,
        unit_amount=unit_amount,
        line_total=qty2 * unit_amount,
        line_no=line_no,
    )
    return po, line_item


@pytest.mark.django_db
def test_production_summary_adds_claims_on_top_of_po_qty():
    user = User.objects.create_user(username="viewer", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store 1")
    product = Product.objects.create(barcode="1234567890123", description="Test Product")

    batch = PurchaseOrderBatch.objects.create(customer=customer)
    po, line_item = _make_po_line(customer, store, product, qty2=10, unit_amount=1, batch=batch)

    Claim.objects.create(purchase_order=po, store=store, product=product, qty=5)

    client = Client()
    client.force_login(user)

    response = client.get(reverse("dashboard:production"))
    assert response.status_code == 200

    row = next(r for r in response.context["totals"] if r["product__barcode"] == "1234567890123")
    assert row["total_qty2"] == 10
    assert row["claimed_qty"] == 5
    assert row["net_qty2"] == 15


@pytest.mark.django_db
def test_production_summary_claims_add_through_with_no_cap():
    user = User.objects.create_user(username="viewer2", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store 1")
    product = Product.objects.create(barcode="9999999999999", description="Big Claim Product")

    batch = PurchaseOrderBatch.objects.create(customer=customer)
    po, line_item = _make_po_line(customer, store, product, qty2=10, unit_amount=1, batch=batch)

    Claim.objects.create(purchase_order=po, store=store, product=product, qty=50)

    client = Client()
    client.force_login(user)

    response = client.get(reverse("dashboard:production"))
    assert response.status_code == 200

    row = next(r for r in response.context["totals"] if r["product__barcode"] == "9999999999999")
    assert row["total_qty2"] == 10
    assert row["claimed_qty"] == 50
    assert row["net_qty2"] == 60

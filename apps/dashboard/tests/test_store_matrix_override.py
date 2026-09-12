import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.core.models import Customer, Product, Store
from apps.dashboard.models import StoreProductOverride
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
def test_staff_can_set_override_when_single_batch_selected():
    staff = User.objects.create_user(username="staffuser", password="testpass123", is_staff=True)
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store 1")
    product = Product.objects.create(barcode="1234567890123", description="Test Product")

    batch = PurchaseOrderBatch.objects.create(customer=customer)
    _make_po_line(customer, store, product, qty2=10, unit_amount=1, batch=batch)

    client = Client()
    client.force_login(staff)

    response = client.get(reverse("dashboard:store_matrix"), {"batch": batch.pk})
    assert response.context["can_override"] is True

    response = client.post(
        reverse("dashboard:set_override"),
        {"batch": batch.pk, "product_id": product.pk, "store_id": store.pk, "override_qty": 99},
    )
    assert response.status_code == 302

    override = StoreProductOverride.objects.get()
    assert override.override_qty == 99
    assert override.updated_by_id == staff.pk

    response = client.get(reverse("dashboard:store_matrix"), {"batch": batch.pk})
    table_rows = {row["product"]["barcode"]: row for row in response.context["table_rows"]}
    cell = table_rows["1234567890123"]["cells"][0]
    assert cell["qty"] == 99
    assert cell["overridden"] is True


@pytest.mark.django_db
def test_non_staff_cannot_set_override():
    user = User.objects.create_user(username="regular", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store 1")
    product = Product.objects.create(barcode="1234567890123", description="Test Product")
    batch = PurchaseOrderBatch.objects.create(customer=customer)
    _make_po_line(customer, store, product, qty2=10, unit_amount=1, batch=batch)

    client = Client()
    client.force_login(user)

    response = client.get(reverse("dashboard:store_matrix"), {"batch": batch.pk})
    assert response.context["can_override"] is False

    response = client.post(
        reverse("dashboard:set_override"),
        {"batch": batch.pk, "product_id": product.pk, "store_id": store.pk, "override_qty": 99},
    )
    assert response.status_code == 403
    assert not StoreProductOverride.objects.exists()


@pytest.mark.django_db
def test_override_ignored_when_no_single_batch_selected():
    staff = User.objects.create_user(username="staffuser2", password="testpass123", is_staff=True)
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store 1")
    product = Product.objects.create(barcode="1234567890123", description="Test Product")
    batch = PurchaseOrderBatch.objects.create(customer=customer)
    _make_po_line(customer, store, product, qty2=10, unit_amount=1, batch=batch)

    StoreProductOverride.objects.create(
        purchase_order_batch=batch, product=product, store=store, override_qty=99, updated_by=staff
    )

    client = Client()
    client.force_login(staff)

    # No batch filter -> override must not apply, and edit controls hidden.
    response = client.get(reverse("dashboard:store_matrix"))
    assert response.context["can_override"] is False
    table_rows = {row["product"]["barcode"]: row for row in response.context["table_rows"]}
    cell = table_rows["1234567890123"]["cells"][0]
    assert cell["qty"] == 10
    assert cell["overridden"] is False

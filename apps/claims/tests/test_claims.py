import pytest
from django.contrib.auth.models import Group, User
from django.test import Client
from django.urls import reverse

from apps.claims.models import Claim
from apps.core.models import Customer, Product, Store
from apps.ingestion.models import POLineItem, PurchaseOrder, PurchaseOrderBatch


def _make_po_with_line(customer, store, product, batch, qty2=10, unit_amount=5, line_no=1):
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
def test_sales_user_can_create_claim_against_batch_store_line_item():
    sales, _ = Group.objects.get_or_create(name="sales")
    user = User.objects.create_user(username="salesuser", password="testpass123")
    user.groups.add(sales)

    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store 1")
    product = Product.objects.create(barcode="1234567890123", description="Test Product")
    batch = PurchaseOrderBatch.objects.create(customer=customer)
    po, line_item = _make_po_with_line(customer, store, product, batch, qty2=10)

    client = Client()
    client.force_login(user)

    response = client.post(
        f"{reverse('claims:list_create')}?batch={batch.pk}&store={po.pk}",
        {"purchase_order": po.pk, "line_item": line_item.pk, "qty": 3, "note": "damaged"},
    )
    assert response.status_code == 302

    claim = Claim.objects.get()
    assert claim.qty == 3
    assert claim.purchase_order_id == po.pk
    assert claim.store_id == store.pk
    assert claim.product_id == product.pk
    assert claim.created_by_id == user.pk


@pytest.mark.django_db
def test_claim_rejects_line_item_not_belonging_to_selected_po():
    sales, _ = Group.objects.get_or_create(name="sales")
    user = User.objects.create_user(username="salesuser", password="testpass123")
    user.groups.add(sales)

    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store 1")
    product = Product.objects.create(barcode="1234567890123", description="Test Product")
    batch = PurchaseOrderBatch.objects.create(customer=customer)

    po_a, line_item_a = _make_po_with_line(customer, store, product, batch, qty2=10)
    po_b, line_item_b = _make_po_with_line(customer, store, product, batch, qty2=20, line_no=2)

    client = Client()
    client.force_login(user)

    # Submitting po_a but a line_item that actually belongs to po_b must be rejected.
    response = client.post(
        f"{reverse('claims:list_create')}?batch={batch.pk}&store={po_a.pk}",
        {"purchase_order": po_a.pk, "line_item": line_item_b.pk, "qty": 3, "note": "damaged"},
    )
    assert response.status_code == 404
    assert not Claim.objects.exists()


@pytest.mark.django_db
def test_batch_first_selection_lists_stores_and_line_items():
    sales, _ = Group.objects.get_or_create(name="sales")
    user = User.objects.create_user(username="salesuser2", password="testpass123")
    user.groups.add(sales)

    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store 1")
    product = Product.objects.create(barcode="1234567890123", description="Nama Pudding Honey")
    batch = PurchaseOrderBatch.objects.create(customer=customer)
    po, line_item = _make_po_with_line(customer, store, product, batch, qty2=10)

    client = Client()
    client.force_login(user)

    response = client.get(reverse("claims:list_create"), {"batch": batch.pk})
    assert response.status_code == 200
    assert response.context["selected_batch"].pk == batch.pk
    assert list(response.context["batch_pos"]) == [po]

    response = client.get(reverse("claims:list_create"), {"batch": batch.pk, "store": po.pk})
    assert response.status_code == 200
    assert response.context["selected_po"].pk == po.pk
    assert b"Nama Pudding Honey" in response.content


@pytest.mark.django_db
def test_non_sales_user_forbidden():
    user = User.objects.create_user(username="prodstaff", password="testpass123")
    client = Client()
    client.force_login(user)

    response = client.get(reverse("claims:list_create"))
    assert response.status_code == 403

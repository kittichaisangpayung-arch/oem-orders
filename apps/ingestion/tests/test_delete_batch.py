import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.claims.models import Claim
from apps.core.models import Customer, Product, Store
from apps.ingestion.models import POLineItem, PurchaseOrder, PurchaseOrderBatch


@pytest.mark.django_db
def test_staff_can_delete_batch_cascades_pos_and_line_items():
    staff = User.objects.create_user(username="staffuser", password="testpass123", is_staff=True)
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store 1")
    product = Product.objects.create(barcode="1234567890123", description="Test Product")

    batch = PurchaseOrderBatch.objects.create(customer=customer)
    po = PurchaseOrder.objects.create(
        batch=batch, customer=customer, store=store,
        store_code_raw=store.store_code, store_name_raw=store.name, source_filename="test.pdf",
    )
    line_item = POLineItem.objects.create(
        purchase_order=po, product=product, barcode_raw=product.barcode,
        description_raw=product.description, qty=10, qty2=10, unit_amount=1, line_total=10, line_no=1,
    )
    claim = Claim.objects.create(purchase_order=po, store=store, product=product, qty=5)

    client = Client()
    client.force_login(staff)

    response = client.post(reverse("ingestion:delete_batch", args=[batch.pk]))
    assert response.status_code == 302

    assert not PurchaseOrderBatch.objects.filter(pk=batch.pk).exists()
    assert not PurchaseOrder.objects.filter(pk=po.pk).exists()
    assert not POLineItem.objects.filter(pk=line_item.pk).exists()

    claim.refresh_from_db()
    assert claim.purchase_order_id is None


@pytest.mark.django_db
def test_non_staff_blocked_from_deleting_batch():
    sales_user = User.objects.create_user(username="salesuser", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    batch = PurchaseOrderBatch.objects.create(customer=customer)

    client = Client()
    client.force_login(sales_user)

    response = client.post(reverse("ingestion:delete_batch", args=[batch.pk]))
    assert response.status_code == 403
    assert PurchaseOrderBatch.objects.filter(pk=batch.pk).exists()


@pytest.mark.django_db
def test_delete_batch_rejects_get():
    staff = User.objects.create_user(username="staffuser2", password="testpass123", is_staff=True)
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    batch = PurchaseOrderBatch.objects.create(customer=customer)

    client = Client()
    client.force_login(staff)

    response = client.get(reverse("ingestion:delete_batch", args=[batch.pk]))
    assert response.status_code == 403
    assert PurchaseOrderBatch.objects.filter(pk=batch.pk).exists()

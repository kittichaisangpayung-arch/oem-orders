import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.core.models import Customer, Product, Store
from apps.dashboard.models import DeliveryNote
from apps.ingestion.models import POLineItem, PurchaseOrder, PurchaseOrderBatch


@pytest.mark.django_db
def test_delivery_note_and_flowaccount_follow_po_line_order():
    user = User.objects.create_user(username="dn-order", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(
        customer=customer, store_code="S1", name="Store One", address="1 Main Rd\r\nBangkok 10110",
    )

    # sort_rank order (A, B, C) deliberately differs from the PO order (C, A, B).
    product_a = Product.objects.create(barcode="1000000000001", description="Product A", sort_rank=1)
    product_b = Product.objects.create(barcode="1000000000002", description="Product B", sort_rank=2)
    product_c = Product.objects.create(barcode="1000000000003", description="Product C", sort_rank=3)

    batch = PurchaseOrderBatch.objects.create(customer=customer)
    po = PurchaseOrder.objects.create(
        batch=batch, customer=customer, store=store,
        store_code_raw=store.store_code, store_name_raw=store.name, source_filename="po.pdf",
    )
    for line_no, product in enumerate([product_c, product_a, product_b], start=1):
        POLineItem.objects.create(
            purchase_order=po, product=product, barcode_raw=product.barcode,
            description_raw=product.description, qty=5, qty2=5,
            unit_amount=10, line_total=50, line_no=line_no,
        )

    client = Client()
    client.force_login(user)

    response = client.post(reverse("dashboard:create_delivery_notes", args=[batch.pk]))
    assert response.status_code == 302

    dn = DeliveryNote.objects.get(batch=batch, store=store)
    items = list(dn.items.all())
    assert [item.product.description for item in items] == ["Product C", "Product A", "Product B"]
    assert [item.line_no for item in items] == [1, 2, 3]

    response = client.get(reverse("dashboard:export_flowaccount_playwright", args=[batch.pk]))
    script = response.content.decode()
    positions = [script.index(f"'{p.barcode}'") for p in (product_c, product_a, product_b)]
    assert positions == sorted(positions)
    assert "branchAddress: '1 Main Rd\\nBangkok 10110'," in script


@pytest.mark.django_db
def test_delivery_note_remarks_min_order_adjustment():
    user = User.objects.create_user(username="dn-remark", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store One")

    bumped = Product.objects.create(barcode="2000000000001", description="Bumped", min_order_qty=10)
    normal = Product.objects.create(barcode="2000000000002", description="Normal", min_order_qty=10)

    batch = PurchaseOrderBatch.objects.create(customer=customer)
    po = PurchaseOrder.objects.create(
        batch=batch, customer=customer, store=store,
        store_code_raw=store.store_code, store_name_raw=store.name, source_filename="po.pdf",
    )
    for line_no, (product, qty) in enumerate([(bumped, 3), (normal, 12)], start=1):
        POLineItem.objects.create(
            purchase_order=po, product=product, barcode_raw=product.barcode,
            description_raw=product.description, qty=qty, qty2=qty,
            unit_amount=1, line_total=qty, line_no=line_no,
        )

    client = Client()
    client.force_login(user)
    client.post(reverse("dashboard:create_delivery_notes", args=[batch.pk]))

    dn = DeliveryNote.objects.get(batch=batch, store=store)
    items = {item.product.description: item for item in dn.items.all()}
    assert items["Bumped"].quantity == 10
    assert items["Bumped"].remark == "ปรับขั้นต่ำ (สั่ง 3)"
    assert items["Normal"].quantity == 12
    assert items["Normal"].remark == ""

    response = client.get(reverse("dashboard:delivery_note_detail", args=[dn.pk]))
    assert "ปรับขั้นต่ำ (สั่ง 3)" in response.content.decode()

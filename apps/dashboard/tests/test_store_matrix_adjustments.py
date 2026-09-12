import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.claims.models import Claim
from apps.core.models import Customer, Product, Store
from apps.ingestion.models import POLineItem, PurchaseOrderBatch, PurchaseOrder


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
def test_store_matrix_adjustment_and_money_totals():
    user = User.objects.create_user(username="viewer", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")

    store_zero = Store.objects.create(customer=customer, store_code="S1", name="Store Zero")
    store_below = Store.objects.create(customer=customer, store_code="S2", name="Store Below")
    store_ok = Store.objects.create(customer=customer, store_code="S3", name="Store OK")

    product_never_ordered = Product.objects.create(
        barcode="1111111111111", description="Never ordered here", min_order_qty=10
    )
    product_below_min = Product.objects.create(
        barcode="2222222222222", description="Below minimum", min_order_qty=10
    )
    product_ok = Product.objects.create(
        barcode="3333333333333", description="At or above minimum", min_order_qty=10
    )

    batch = PurchaseOrderBatch.objects.create(customer=customer)

    # store_zero never orders product_never_ordered, but store_below does --
    # so the product still appears as a matrix row, with a 0/unadjusted cell
    # for the store that skipped it.
    _make_po_line(customer, store_below, product_never_ordered, qty2=20, unit_amount=1, batch=batch)

    _make_po_line(customer, store_zero, product_below_min, qty2=3, unit_amount=2, batch=batch, line_no=2)
    _make_po_line(customer, store_zero, product_ok, qty2=15, unit_amount=5, batch=batch, line_no=3)

    _make_po_line(customer, store_below, product_below_min, qty2=4, unit_amount=2, batch=batch, line_no=2)
    _make_po_line(customer, store_ok, product_ok, qty2=12, unit_amount=5, batch=batch)

    client = Client()
    client.force_login(user)

    response = client.get(reverse("dashboard:store_matrix"))
    assert response.status_code == 200

    table_rows = {row["product"]["barcode"]: row for row in response.context["table_rows"]}
    store_names = response.context["store_names"]

    def cell_for(barcode, store_name):
        idx = store_names.index(store_name)
        return table_rows[barcode]["cells"][idx]

    # Never-ordered-by-this-store product: stays 0, not adjusted, even though min_order_qty is 10.
    cell = cell_for("1111111111111", "Store Zero")
    assert cell["qty"] == 0
    assert cell["adjusted"] is False

    cell = cell_for("1111111111111", "Store Below")
    assert cell["qty"] == 20
    assert cell["adjusted"] is False

    # Below-minimum orders get bumped up to the minimum and flagged adjusted.
    cell = cell_for("2222222222222", "Store Zero")
    assert cell["qty"] == 10
    assert cell["adjusted"] is True

    cell = cell_for("2222222222222", "Store Below")
    assert cell["qty"] == 10
    assert cell["adjusted"] is True

    # At/above minimum: unchanged, not adjusted.
    cell = cell_for("3333333333333", "Store Zero")
    assert cell["qty"] == 15
    assert cell["adjusted"] is False

    cell = cell_for("3333333333333", "Store OK")
    assert cell["qty"] == 12
    assert cell["adjusted"] is False

    # Money totals: store_zero = 3*2 + 15*5 = 81; store_below = 20*1 + 4*2 = 28; store_ok = 12*5 = 60.
    totals_by_name = {row["name"]: row["total_amount"] for row in response.context["store_totals"]}
    assert totals_by_name["Store Zero"] == 81
    assert totals_by_name["Store Below"] == 28
    assert totals_by_name["Store OK"] == 60
    assert response.context["grand_total"] == 81 + 28 + 60


@pytest.mark.django_db
def test_store_matrix_claim_adds_to_qty_before_min_order_bump():
    user = User.objects.create_user(username="viewer3", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")

    store_a = Store.objects.create(customer=customer, store_code="S1", name="Store A")
    store_b = Store.objects.create(customer=customer, store_code="S2", name="Store B")
    store_c = Store.objects.create(customer=customer, store_code="S3", name="Store C")

    # Ordered 3, min_order_qty 10: a claim of 5 nets to 8, still below
    # minimum, so it should still get bumped up to 10 and flagged adjusted.
    product = Product.objects.create(barcode="4444444444444", description="Claimed product", min_order_qty=10)

    batch = PurchaseOrderBatch.objects.create(customer=customer)
    po_a, _ = _make_po_line(customer, store_a, product, qty2=3, unit_amount=1, batch=batch)
    po_b, _ = _make_po_line(customer, store_b, product, qty2=20, unit_amount=1, batch=batch, line_no=2)
    # store_c never orders this product at all, but a claim can still land
    # against a PO of theirs for some other product, resolving store_c into
    # existence; the claim below targets store_c directly via a PO of theirs.
    po_c, _ = _make_po_line(customer, store_c, product, qty2=0, unit_amount=1, batch=batch, line_no=3)

    Claim.objects.create(purchase_order=po_a, store=store_a, product=product, qty=5)
    Claim.objects.create(purchase_order=po_c, store=store_c, product=product, qty=7)

    client = Client()
    client.force_login(user)

    response = client.get(reverse("dashboard:store_matrix"))
    assert response.status_code == 200

    table_rows = {row["product"]["barcode"]: row for row in response.context["table_rows"]}
    store_names = response.context["store_names"]

    def cell_for(barcode, store_name):
        idx = store_names.index(store_name)
        return table_rows[barcode]["cells"][idx]

    # Store A: 3 + 5 claimed = 8, still below min_order_qty of 10 -> bumped to 10, adjusted.
    cell = cell_for("4444444444444", "Store A")
    assert cell["qty"] == 10
    assert cell["adjusted"] is True

    # Store B: no claim, 20 stays at 20, not adjusted.
    cell = cell_for("4444444444444", "Store B")
    assert cell["qty"] == 20
    assert cell["adjusted"] is False

    # Store C: ordered 0, but a claim of 7 makes it non-zero -> now eligible
    # for the min-qty bump too, since claims can turn a real zero into a
    # real order that still needs to meet the minimum.
    cell = cell_for("4444444444444", "Store C")
    assert cell["qty"] == 10
    assert cell["adjusted"] is True

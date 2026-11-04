from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Customer, Store
from apps.dashboard.models import DeliveryNote, Invoice, InvoiceLineItem


@pytest.mark.django_db
def test_billing_statement_line_amount_excludes_vat():
    user = User.objects.create_user(username="biller", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store One")
    DeliveryNote.objects.create(
        store=store,
        delivery_address="addr",
        subtotal=Decimal("100.00"),
        vat_amount=Decimal("7.00"),
        grand_total=Decimal("107.00"),
    )

    client = Client()
    client.force_login(user)
    now = timezone.now()
    response = client.post(
        reverse("dashboard:create_billing_statement"),
        {"customer_id": customer.id, "year_month": f"{now.year}-{now.month}"},
    )
    assert response.status_code == 302

    invoice = Invoice.objects.get(customer=customer)
    assert [item.amount for item in invoice.line_items.all()] == [Decimal("100.00")]
    assert invoice.subtotal == Decimal("100.00")
    assert invoice.grand_total == Decimal("107.00")


@pytest.mark.django_db
def test_billing_statement_paginates_10_items_per_page_with_header():
    user = User.objects.create_user(username="biller", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    invoice = Invoice.objects.create(
        customer=customer,
        invoice_month=10,
        invoice_year=2026,
        invoice_type=Invoice.InvoiceType.BILLING_STATEMENT,
    )
    for n in range(1, 24):
        InvoiceLineItem.objects.create(
            invoice=invoice, description="x", quantity=1, amount=Decimal("1"), line_no=n
        )

    client = Client()
    client.force_login(user)
    response = client.get(reverse("dashboard:invoice_detail", args=[invoice.id]))
    assert response.status_code == 200

    assert [len(page) for page in response.context["pages"]] == [10, 10, 3]
    html = response.content.decode()
    assert html.count("รายการสินค้า / Description") == 3
    assert "BILLING STATEMENT (หน้า 3)" in html
    assert "BILLING STATEMENT (หน้า 4)" in html
    assert html.count("รวมเงิน (ยังไม่รวม VAT) / Subtotal") == 1


@pytest.mark.django_db
def test_edit_invoice_adds_and_deletes_line_items_and_recalculates_totals():
    user = User.objects.create_user(username="biller", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    invoice = Invoice.objects.create(
        customer=customer,
        invoice_month=10,
        invoice_year=2026,
        invoice_type=Invoice.InvoiceType.BILLING_STATEMENT,
        subtotal=Decimal("300"),
        vat_amount=Decimal("21"),
        grand_total=Decimal("321"),
    )
    keep = InvoiceLineItem.objects.create(
        invoice=invoice, description="old", quantity=5, amount=Decimal("100"), line_no=1
    )
    drop = InvoiceLineItem.objects.create(
        invoice=invoice, description="old", quantity=5, amount=Decimal("200"), line_no=2
    )

    client = Client()
    client.force_login(user)
    response = client.post(
        reverse("dashboard:edit_invoice", args=[invoice.id]),
        {
            "invoice_number": invoice.invoice_number,
            "po_numbers": "",
            "default_description": "Cake",
            f"invoice_no_{keep.id}": "IV-1",
            f"invoice_no_{drop.id}": "IV-2",
            "delete_item": [str(drop.id)],
            "new_invoice_no": ["IV-9", ""],
            "new_quantity": ["3", ""],
            "new_unit": ["PCS", "PCS"],
            "new_amount": ["1,000.50", ""],
        },
    )
    assert response.status_code == 302

    items = list(invoice.line_items.order_by("line_no"))
    assert [(i.line_no, i.external_invoice_number, i.quantity, i.amount, i.description) for i in items] == [
        (1, "IV-1", 5, Decimal("100.00"), "Cake"),
        (2, "IV-9", 3, Decimal("1000.50"), "Cake"),
    ]
    invoice.refresh_from_db()
    assert invoice.subtotal == Decimal("1100.50")
    assert invoice.vat_amount == Decimal("77.04")
    assert invoice.grand_total == Decimal("1177.54")


@pytest.mark.django_db
def test_edit_invoice_rejects_invalid_new_amount_without_changes():
    user = User.objects.create_user(username="biller", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    invoice = Invoice.objects.create(customer=customer, invoice_month=10, invoice_year=2026)
    item = InvoiceLineItem.objects.create(
        invoice=invoice, description="old", quantity=5, amount=Decimal("100"), line_no=1
    )

    client = Client()
    client.force_login(user)
    response = client.post(
        reverse("dashboard:edit_invoice", args=[invoice.id]),
        {
            "invoice_number": invoice.invoice_number,
            "delete_item": [str(item.id)],
            "new_invoice_no": ["IV-9"],
            "new_quantity": ["3"],
            "new_unit": ["PCS"],
            "new_amount": ["abc"],
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboard:edit_invoice", args=[invoice.id])
    assert list(invoice.line_items.values_list("id", flat=True)) == [item.id]


@pytest.mark.django_db
def test_new_delivery_notes_are_appended_to_existing_billing_statement():
    from apps.dashboard.views import _sync_billing_statements_for_delivery_notes

    user = User.objects.create_user(username="biller", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store One")
    DeliveryNote.objects.create(store=store, delivery_address="addr", subtotal=Decimal("100.00"))

    client = Client()
    client.force_login(user)
    now = timezone.localtime()
    client.post(
        reverse("dashboard:create_billing_statement"),
        {"customer_id": customer.id, "year_month": f"{now.year}-{now.month}"},
    )
    invoice = Invoice.objects.get(customer=customer)
    first = invoice.line_items.get()
    first.external_invoice_number = "IV-1"
    first.save()
    InvoiceLineItem.objects.create(
        invoice=invoice, description="manual", quantity=1, amount=Decimal("50"), line_no=2
    )

    dn2 = DeliveryNote.objects.create(store=store, delivery_address="addr", subtotal=Decimal("200.00"))
    _sync_billing_statements_for_delivery_notes([dn2])

    items = list(invoice.line_items.order_by("line_no"))
    assert [(i.line_no, i.external_invoice_number, i.amount) for i in items] == [
        (1, "IV-1", Decimal("100.00")),
        (2, "", Decimal("50.00")),
        (3, "", Decimal("200.00")),
    ]
    assert items[2].delivery_note == dn2
    invoice.refresh_from_db()
    assert invoice.subtotal == Decimal("350.00")
    assert invoice.grand_total == Decimal("374.50")

    # Re-submitting the create form syncs again without duplicating lines
    dn3 = DeliveryNote.objects.create(store=store, delivery_address="addr", subtotal=Decimal("10.00"))
    client.post(
        reverse("dashboard:create_billing_statement"),
        {"customer_id": customer.id, "year_month": f"{now.year}-{now.month}"},
    )
    assert Invoice.objects.filter(customer=customer).count() == 1
    assert list(invoice.line_items.exclude(delivery_note=None).order_by("line_no")
                .values_list("delivery_note_id", flat=True)) == [first.delivery_note_id, dn2.id, dn3.id]

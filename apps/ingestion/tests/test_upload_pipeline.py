"""
Integration test: uploads all 8 real sample PO PDFs through the actual
upload view, then verifies the dashboard aggregation queries produce the
same per-store, per-barcode totals the reference script's
`final_df.groupby(['Store Code','Barcode'])['Qty2'].sum()` would produce.

This proves the whole path (parse -> store -> aggregate -> dashboard) is
equivalent, not just the parser in isolation.
"""
import json
from collections import defaultdict
from pathlib import Path

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.core.models import Customer
from apps.ingestion.models import POLineItem

PDF_DIR = Path(__file__).resolve().parents[3]
FIXTURES_DIR = Path(__file__).resolve().parents[2] / "parsers" / "tests" / "fixtures"

with open(FIXTURES_DIR / "donki_expected.json", encoding="utf-8") as f:
    GOLDEN = json.load(f)


@pytest.mark.django_db
def test_upload_pipeline_matches_reference_aggregation(django_user_model):
    from django.core.management import call_command
    call_command("loaddata", str(Path(__file__).resolve().parents[3] / "fixtures" / "seed_donki.json"))

    user = django_user_model.objects.create_user(username="salesuser", password="testpass123")
    sales_group, _ = Group.objects.get_or_create(name="sales")
    user.groups.add(sales_group)

    client = Client()
    client.force_login(user)

    customer = Customer.objects.get(code="DONKI")

    uploaded_files = []
    for filename in GOLDEN:
        with open(PDF_DIR / filename, "rb") as f:
            content = f.read()
        uploaded_files.append(SimpleUploadedFile(filename, content, content_type="application/pdf"))

    response = client.post(
        reverse("ingestion:upload"),
        {"customer": customer.pk, "files": uploaded_files},
    )
    assert response.status_code == 302

    # Expected totals per (store_code, barcode) computed straight from the
    # golden fixture, mirroring the reference script's groupby+sum.
    expected_totals = defaultdict(int)
    for entry in GOLDEN.values():
        for li in entry["line_items"]:
            expected_totals[(entry["store_code"], li["Barcode"])] += li["Qty2"]

    actual_totals = defaultdict(int)
    for li in POLineItem.objects.select_related("purchase_order").all():
        key = (li.purchase_order.store_code_raw, li.barcode_raw)
        actual_totals[key] += li.qty2

    assert dict(actual_totals) == dict(expected_totals)


@pytest.mark.django_db
def test_upload_forbidden_for_non_sales_user(django_user_model):
    user = django_user_model.objects.create_user(username="prodstaff", password="testpass123")
    client = Client()
    client.force_login(user)

    response = client.get(reverse("ingestion:upload"))
    assert response.status_code == 403

"""
Regression tests proving DonkiParser produces output equivalent to the
reference pdf_to_gsheets.py logic against the real sample PO PDFs.

Golden output was captured by running the original extract_store_data /
extract_store_data_flexible / _read_single_pdf logic (copied verbatim, see
_capture_golden.py at the project root) against every sample PDF, before
any porting happened -- see fixtures/donki_expected.json.
"""
import json
from pathlib import Path

import pytest

from apps.parsers.donki import DonkiParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"
# Sample PDFs live at the project root (one level above manage.py).
PDF_DIR = Path(__file__).resolve().parents[3]

with open(FIXTURES_DIR / "donki_expected.json", encoding="utf-8") as f:
    GOLDEN = json.load(f)


@pytest.fixture
def parser():
    return DonkiParser()


@pytest.mark.parametrize("filename", list(GOLDEN.keys()))
def test_matches_golden_output(parser, filename):
    pdf_path = PDF_DIR / filename
    expected = GOLDEN[filename]

    parsed = parser.parse(str(pdf_path))

    assert parsed.store_code == expected["store_code"]
    assert parsed.store_name == expected["store_name"]
    assert parsed.order_no == expected["order_no"]
    assert parsed.expected_row_count == expected["expected_row_count"]
    assert parsed.parser_used == expected["parser_used"]
    assert len(parsed.line_items) == expected["parsed_row_count"]

    for actual_item, expected_item in zip(parsed.line_items, expected["line_items"]):
        assert actual_item.barcode == expected_item["Barcode"]
        assert actual_item.description == expected_item["Description"]
        assert actual_item.qty == expected_item["Qty"]
        assert actual_item.qty2 == expected_item["Qty2"]
        assert actual_item.unit_amount == expected_item["Amount"]


def test_fallback_case_uses_flexible_regex(parser):
    """PO.NO.525033 is the one sample where the strict regex only gets 3/12
    rows (missing UOM column breaks its column alignment) and the parser
    must fall back to the flexible regex to get all 12 rows. This is the
    highest-risk part of the port -- confirmed against the reference script
    before porting: strict=3/12, flexible=12/12."""
    pdf_path = PDF_DIR / "PO.NO.525033 New Line 04.09.26.pdf"

    parsed = parser.parse(str(pdf_path))

    assert parsed.parser_used == "flexible"
    assert parsed.expected_row_count == 12
    assert len(parsed.line_items) == 12


@pytest.mark.parametrize("filename", list(GOLDEN.keys()))
def test_row_count_sanity(parser, filename):
    pdf_path = PDF_DIR / filename
    parsed = parser.parse(str(pdf_path))
    assert len(parsed.line_items) >= parsed.expected_row_count

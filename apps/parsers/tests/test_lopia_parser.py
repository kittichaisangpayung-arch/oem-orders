"""
Tests for LopiaParser against the sample PO_Lopia.pdf
"""
from pathlib import Path

import pytest

from apps.parsers.lopia import LopiaParser

# Sample PDF lives at the project root
PDF_DIR = Path(__file__).resolve().parents[3]


@pytest.fixture
def parser():
    return LopiaParser()


def test_lopia_basic_parsing(parser):
    """Test basic parsing of Lopia PO PDF"""
    pdf_path = PDF_DIR / "PO_Lopia.pdf"

    parsed = parser.parse(str(pdf_path))

    assert parsed.store_code == "9001"
    assert parsed.store_name == "LOPIA"
    assert parsed.order_no == "PO-2609-0969"
    assert parsed.expected_row_count == 2
    assert len(parsed.line_items) == 2
    assert parsed.parser_used == "strict"


def test_lopia_line_items(parser):
    """Test that line items are parsed correctly with all fields"""
    pdf_path = PDF_DIR / "PO_Lopia.pdf"

    parsed = parser.parse(str(pdf_path))

    # First item
    item1 = parsed.line_items[0]
    assert item1.barcode == "8858911200956"
    assert "GREEK YOGURT BUTTERFLY" in item1.description
    assert item1.uom == "Pieces"
    assert item1.qty == 45
    assert item1.qty2 == 45
    assert item1.unit_amount == 60.0
    assert item1.line_total == 2700.0
    assert item1.line_no == 1

    # Second item
    item2 = parsed.line_items[1]
    assert item2.barcode == "8858911201571"
    assert "GREEK YOGURT BUTTERFLY" in item2.description
    assert item2.uom == "Pieces"
    assert item2.qty == 45
    assert item2.qty2 == 45
    assert item2.unit_amount == 40.0
    assert item2.line_total == 1800.0
    assert item2.line_no == 2


def test_lopia_total_amount(parser):
    """Test that total amounts sum correctly"""
    pdf_path = PDF_DIR / "PO_Lopia.pdf"

    parsed = parser.parse(str(pdf_path))

    total = sum(item.line_total for item in parsed.line_items)
    assert total == 4500.0  # 2700 + 1800


def test_lopia_row_count_sanity(parser):
    """Ensure parsed rows match or exceed expected count"""
    pdf_path = PDF_DIR / "PO_Lopia.pdf"

    parsed = parser.parse(str(pdf_path))

    assert len(parsed.line_items) >= parsed.expected_row_count

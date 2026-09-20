"""
Parser for Lopia (Thailand) Co., Ltd. PO PDFs.

Structure is different from Donki:
- Header: Order No., Order Date in top section
- Delivery Address contains store information
- Products: Barcode, Description, UoM, Quantity, Unit Cost, Amount
- Uses "Pieces" as UoM instead of "PCS"
"""
import re

import pdfplumber

from .base import BasePOParser, ParsedLineItem, ParsedPO, ParserError
from .registry import register

# Header patterns
_RE_ORDER_NO = re.compile(r"Order No\.\s*:\s*(\S+)")
_RE_DELIVERY_ADDRESS = re.compile(r"Delivery Address\s+(.+?)\s+(?:Central|Tel:)", re.DOTALL)

# Product line pattern - Lopia format:
# Date Barcode Description UoM DirectCost Quantity Discount Amount
# Example: 2026/09/24 8858911200956 GREEK YOGURT BUTTERFLY Pieces 45.00 60 0.00 2,700.00
# Field mapping: (1)Barcode (2)Description (3)UoM (4)DirectCost(UnitPrice) (5)Quantity (6)Discount (7)Amount
_RE_PRODUCTS = re.compile(
    r"\d{4}/\d{2}/\d{2}\s+(\d{13})\s+(.+?)\s+(Pieces|PCS|BOX|pcs|pieces)\s+([\d\.]+)\s+([\d\.]+)\s+([\d,\.]+)\s+([\d,\.]+)"
)

# Alternative pattern without UoM (flexible)
# Captures: (1)Barcode (2)Description (3)DirectCost (4)Quantity (5)Discount (6)Amount
_RE_FLEX = re.compile(
    r"\d{4}/\d{2}/\d{2}\s+(\d{13})\s+(.+?)\s+([\d\.]+)\s+([\d\.]+)\s+([\d,\.]+)\s+([\d,\.]+)"
)

# Count expected rows by barcodes
_RE_ROW_BARCODE = re.compile(r"(?m)^[^\d]*(\d{13})\b")


def _to_float(val: str) -> float:
    try:
        return float(val.replace(",", ""))
    except ValueError:
        return 0.0


@register("lopia_v1")
class LopiaParser(BasePOParser):
    def parse(self, pdf_path: str) -> ParsedPO:
        text = self._extract_text(pdf_path)
        if not text.strip():
            raise ParserError(f"No extractable text in {pdf_path}")

        order_no = self._parse_order_no(text)
        store_name = self._parse_store_name(text)
        store_code = self._derive_store_code(store_name)
        expected_row_count = len(set(_RE_ROW_BARCODE.findall(text)))

        line_items = self._extract_strict(text)
        parser_used = "strict"

        if not line_items or len(line_items) < expected_row_count:
            flex_items = self._extract_flexible(text)
            if len(flex_items) > len(line_items):
                line_items = flex_items
                parser_used = "flexible"

        return ParsedPO(
            store_code=store_code,
            store_name=store_name,
            order_no=order_no,
            line_items=line_items,
            expected_row_count=expected_row_count,
            parser_used=parser_used,
            raw_text=text,
        )

    def _extract_text(self, pdf_path: str) -> str:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        return text

    def _parse_order_no(self, text: str) -> str:
        match = _RE_ORDER_NO.search(text)
        return match.group(1).strip() if match else "Unknown"

    def _parse_store_name(self, text: str) -> str:
        """Extract store name from Delivery Address section"""
        match = _RE_DELIVERY_ADDRESS.search(text)
        if match:
            # First line of delivery address is usually the store name
            lines = match.group(1).strip().split('\n')
            if lines:
                return lines[0].strip()
        return "Unknown Store"

    def _derive_store_code(self, store_name: str) -> str:
        """
        Derive store code from store name.
        For Lopia, we'll use 9001 as the base code (from customers_config.json)
        """
        # Check if store name contains identifiable location
        name_lower = store_name.lower()
        if "chaengwattana" in name_lower or "central chaengwattana" in name_lower:
            return "9001"
        # Add more mappings as needed
        return "9001"

    def _extract_strict(self, text: str) -> list[ParsedLineItem]:
        items = []
        for line_no, (barcode, desc, uom, direct_cost, qty, discount, amount) in enumerate(
            _RE_PRODUCTS.findall(text), start=1
        ):
            qty_float = float(qty)
            qty_int = int(qty_float)
            amount_float = _to_float(amount)
            unit_cost_float = float(direct_cost)  # Field 4 is the unit cost

            items.append(ParsedLineItem(
                barcode=barcode,
                description=desc.strip(),
                uom=uom.capitalize(),  # Normalize to "Pieces"
                qty=qty_int,
                qty2=qty_int,  # Lopia uses quantity directly
                unit_amount=unit_cost_float,
                line_total=amount_float,
                line_no=line_no,
            ))
        return items

    def _extract_flexible(self, text: str) -> list[ParsedLineItem]:
        items = []
        for line_no, (barcode, desc, direct_cost, qty, discount, amount) in enumerate(
            _RE_FLEX.findall(text), start=1
        ):
            qty_float = float(qty)
            qty_int = int(qty_float)
            amount_float = _to_float(amount)
            unit_cost_float = float(direct_cost)  # Field 3 is the unit cost

            items.append(ParsedLineItem(
                barcode=barcode,
                description=desc.strip(),
                uom="Pieces",
                qty=qty_int,
                qty2=qty_int,
                unit_amount=unit_cost_float,
                line_total=amount_float,
                line_no=line_no,
            ))
        return items

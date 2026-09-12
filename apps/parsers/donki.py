"""
Parser for Donki (Thailand) Co., Ltd. PO PDFs.

Ported from the reference script pdf_to_gsheets.py (regex patterns and
extraction logic lines 133-249), which has been used in production. The
strict/flexible dual-regex fallback exists because some vendor PDFs omit
the UOM column, which silently breaks the strict pattern's column alignment.
Whichever regex yields more rows (compared against the count of lines that
start with a 13-digit barcode -- the "expected" row count) wins.
"""
import re

import pdfplumber

from .base import BasePOParser, ParsedLineItem, ParsedPO, ParserError
from .registry import register

_RE_STORE = re.compile(r"Store Name\s+([^\n]+?)(?:\s+Vendor Name|$)", re.MULTILINE)
_RE_STORE_CODE = re.compile(r"Store Code\s+(\S+)")
_RE_ORDER_NO = re.compile(r"Order No\.\s+(\S+)")

# Strict pattern -- works when the PDF has a clear UOM column (e.g. PCS, BOX).
_RE_PRODUCTS = re.compile(
    r"(\d{13})\s+([A-Za-z0-9 ]+?)\s+([A-Z]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d,\.]+)"
)
# Flexible fallback -- for PDFs where the UOM column is blank/absent.
_RE_FLEX = re.compile(
    r"(\d{13})\s+(.+?)\s+(\d+)\s+(\d+)\s+\d+\s+([\d,\.]+)\s+\w+\s+\w+\s+([\d,\.]+)"
)
# Counts how many product rows should actually exist, by counting lines that
# start with a 13-digit barcode. Used to sanity-check strict vs flexible.
_RE_ROW_BARCODE = re.compile(r"(?m)^(\d{13})\b")


def _to_float(val: str) -> float:
    try:
        return float(val.replace(",", ""))
    except ValueError:
        return 0.0


@register("donki_v1")
class DonkiParser(BasePOParser):
    def parse(self, pdf_path: str) -> ParsedPO:
        text = self._extract_text(pdf_path)
        if not text.strip():
            raise ParserError(f"No extractable text in {pdf_path}")

        store_code, store_name, order_no = self._parse_header(text)
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

    def _parse_header(self, text: str) -> tuple[str, str, str]:
        store_match = _RE_STORE.search(text)
        store_name = store_match.group(1).strip() if store_match else "Unknown Store"

        code_match = _RE_STORE_CODE.search(text)
        store_code = code_match.group(1).strip() if code_match else "Unknown"

        order_match = _RE_ORDER_NO.search(text)
        order_no = order_match.group(1).strip() if order_match else "Unknown"

        return store_code, store_name, order_no

    def _extract_strict(self, text: str) -> list[ParsedLineItem]:
        items = []
        for line_no, (barcode, desc, uom, qty, qty2, _box, amount) in enumerate(
            _RE_PRODUCTS.findall(text), start=1
        ):
            qty2_int = int(qty2)
            amt = _to_float(amount)
            items.append(ParsedLineItem(
                barcode=barcode,
                description=desc.strip(),
                uom=uom,
                qty=int(qty),
                qty2=qty2_int,
                unit_amount=amt,
                line_total=qty2_int * amt,
                line_no=line_no,
            ))
        return items

    def _extract_flexible(self, text: str) -> list[ParsedLineItem]:
        items = []
        for line_no, (barcode, desc, qty, qty2, amount, total) in enumerate(
            _RE_FLEX.findall(text), start=1
        ):
            items.append(ParsedLineItem(
                barcode=barcode,
                description=desc.strip(),
                uom="PCS",
                qty=int(qty),
                qty2=int(qty2),
                unit_amount=_to_float(amount),
                line_total=_to_float(total),
                line_no=line_no,
            ))
        return items

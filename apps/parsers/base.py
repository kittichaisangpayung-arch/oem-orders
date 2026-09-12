"""
Common interface every customer-specific PO PDF parser must implement.

Each customer's PO PDF template is different, so each customer gets its own
parser module (see donki.py for the first concrete example). The interface
deliberately only guarantees `parse(pdf_path) -> ParsedPO` -- any fallback
strategy, sanity-checking, or multi-regex logic a given customer's PDFs need
is that parser's own internal business, not part of this contract. This is
what lets a new customer's parser be added without touching existing ones.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedLineItem:
    barcode: str
    description: str
    uom: str
    qty: int
    qty2: int
    unit_amount: float
    line_total: float
    line_no: int


@dataclass
class ParsedPO:
    store_code: str
    store_name: str
    order_no: str
    line_items: list[ParsedLineItem] = field(default_factory=list)
    expected_row_count: int = 0
    parser_used: str = ""
    raw_text: str = ""


class ParserError(Exception):
    """Raised when a PDF cannot be parsed at all (e.g. no extractable text)."""


class BasePOParser(ABC):
    @abstractmethod
    def parse(self, pdf_path: str) -> ParsedPO:
        """Parse a single PO PDF file and return a ParsedPO.

        Raise ParserError for unrecoverable failures (e.g. empty/corrupt PDF).
        Partial parses (some rows extracted but fewer than expected) should
        still return a ParsedPO -- the caller decides how to surface that via
        expected_row_count vs len(line_items).
        """

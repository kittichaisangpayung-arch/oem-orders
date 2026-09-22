"""
Quick demo script showing Lopia parser in action
"""
import sys
sys.path.insert(0, 'apps')

from parsers import lopia
from parsers.registry import get_parser

print("=" * 80)
print("LOPIA PARSER DEMO")
print("=" * 80)
print()

# Get parser from registry
parser = get_parser("lopia_v1")
result = parser.parse("PO_Lopia.pdf")

print(f"Order: {result.order_no}")
print(f"Store: {result.store_name} (Code: {result.store_code})")
print(f"Items: {len(result.line_items)}/{result.expected_row_count} (Parser: {result.parser_used})")
print()

print("Items:")
print("-" * 80)
total = 0
for item in result.line_items:
    print(f"{item.line_no}. {item.barcode}")
    print(f"   {item.description}")
    print(f"   {item.qty} {item.uom} x {item.unit_amount:,.2f} = {item.line_total:,.2f} THB")
    total += item.line_total

print("-" * 80)
print(f"Total: {total:,.2f} THB")
print()
print("Parser implementation complete!")

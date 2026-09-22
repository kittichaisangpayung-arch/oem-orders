"""Test Lopia parser with corrected unit cost calculation"""
import sys
sys.path.insert(0, 'apps')

from parsers.lopia import LopiaParser

parser = LopiaParser()
result = parser.parse("PO_Lopia.pdf")

print(f"Store Code: {result.store_code}")
print(f"Store Name: {result.store_name}")
print(f"Order No: {result.order_no}")
print(f"Parser Used: {result.parser_used}")
print(f"Expected Rows: {result.expected_row_count}")
print(f"Parsed Rows: {len(result.line_items)}")
print()

print("Line Items:")
print("-" * 100)
for item in result.line_items:
    print(f"Line {item.line_no}: {item.barcode}")
    print(f"  Description: {item.description}")
    print(f"  UoM: {item.uom}")
    print(f"  Quantity: {item.qty} (Qty2: {item.qty2})")
    print(f"  Unit Amount: {item.unit_amount:,.2f} THB")
    print(f"  Line Total: {item.line_total:,.2f} THB")
    print(f"  Calculation Check: {item.qty} x {item.unit_amount:.2f} = {item.qty * item.unit_amount:,.2f}")
    print()

total = sum(item.line_total for item in result.line_items)
print(f"Grand Total: {total:,.2f} THB")
print()
print("Expected values:")
print("  Item 1: 45 qty x 60 = 2,700")
print("  Item 2: 45 qty x 40 = 1,800")
print("  Total: 4,500")

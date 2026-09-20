# Lopia Parser Implementation

## Overview
Parser สำหรับอ่าน Purchase Order PDF ของ Lopia (Thailand) Co., Ltd. ทำงานคล้ายกับ Donki parser แต่ปรับให้เข้ากับรูปแบบ PDF ของ Lopia

## Files Created/Modified

### New Files:
1. `apps/parsers/lopia.py` - Lopia parser implementation
2. `apps/parsers/tests/test_lopia_parser.py` - Unit tests for Lopia parser

### Modified Files:
1. `apps/parsers/apps.py` - ลงทะเบียน LopiaParser ให้โหลดตอน Django startup

## Key Features

### PDF Structure (Lopia)
```
Delivery Date | Barcode (13 digits) | Description | UoM | Quantity | Direct Cost | Discount | Amount
2026/09/24    | 8858911200956      | GREEK YOGURT | Pieces | 45.00 | 60 | 0.00 | 2,700.00
```

### Differences from Donki:
- **Date Column**: มี Delivery Date อยู่หน้าแถวสินค้า
- **Store Information**: อยู่ใน Delivery Address section แทน Store Name/Store Code
- **UoM**: ใช้ "Pieces" แทน "PCS"
- **Quantity**: เป็นทศนิยม (45.00) แทนจำนวนเต็ม

## Usage

### Through Registry (Production):
```python
from apps.parsers.registry import get_parser

parser = get_parser("lopia_v1")
result = parser.parse("/path/to/PO_Lopia.pdf")

print(f"Store: {result.store_name} ({result.store_code})")
print(f"Order No: {result.order_no}")
print(f"Items: {len(result.line_items)}")

for item in result.line_items:
    print(f"{item.barcode} - {item.description}")
    print(f"  Qty: {item.qty2} x {item.unit_amount} = {item.line_total}")
```

### Direct Import (Testing):
```python
from apps.parsers.lopia import LopiaParser

parser = LopiaParser()
result = parser.parse("PO_Lopia.pdf")
```

## Configuration

### Store Code Mapping
Currently configured in `customers_config.json`:
```json
"9001": {
  "name": "Lopia Trading Co., Ltd.",
  "address": "XYZ Tower, 18th Floor...",
  "delivery_address": "Lopia Central Chaengwattana...",
  "tax_id": "0105551234567"
}
```

### Parser Key
- **Registry Key**: `lopia_v1`
- **Class**: `LopiaParser`
- **Decorator**: `@register("lopia_v1")`

## Implementation Details

### Regex Patterns

**Strict Pattern** (with UoM):
```python
_RE_PRODUCTS = re.compile(
    r"\d{4}/\d{2}/\d{2}\s+(\d{13})\s+(.+?)\s+(Pieces|PCS|BOX|pcs|pieces)\s+([\d\.]+)\s+[\d\.]+\s+([\d,\.]+)\s+([\d,\.]+)"
)
```

**Flexible Pattern** (without UoM):
```python
_RE_FLEX = re.compile(
    r"\d{4}/\d{2}/\d{2}\s+(\d{13})\s+(.+?)\s+([\d\.]+)\s+[\d\.]+\s+([\d,\.]+)\s+([\d,\.]+)"
)
```

### Fallback Strategy
1. พยายามใช้ strict pattern ก่อน (มี UoM)
2. ถ้าได้น้อยกว่าจำนวนที่คาดหวัง ใช้ flexible pattern
3. เลือกผลลัพธ์ที่ได้มากกว่า

### Unit Cost Calculation
- อ่านจากคอลัมน์ Unit Cost (ตำแหน่งที่ 5)
- ถ้าเป็น 0 จะคำนวณจาก: Amount / Quantity

## Testing

### Run Tests:
```bash
pytest apps/parsers/tests/test_lopia_parser.py -v
```

### Test Coverage:
- ✅ Basic parsing (store, order no, item count)
- ✅ Line item details (barcode, description, quantities, amounts)
- ✅ Total amount calculation
- ✅ Row count sanity check

## Sample Output

```
Store Code: 9001
Store Name: LOPIA
Order No: PO-2609-0969
Parser Used: strict
Expected Rows: 2
Parsed Rows: 2

Line Items:
Line 1: 8858911200956 | GREEK YOGURT BUTTERFLY ORGANIC           | Pieces   | Qty:  45 | Qty2:  45 | Unit:    60.00 | Total:    2700.00
Line 2: 8858911201571 | GREEK YOGURT BUTTERFLY ORGANIC VANILLA   | Pieces   | Qty:  45 | Qty2:  45 | Unit:    40.00 | Total:    1800.00
```

## Integration with Existing System

Parser สามารถใช้งานร่วมกับระบบที่มีอยู่แล้วได้ทันที:
1. ลงทะเบียนใน registry เรียบร้อยแล้ว
2. ใช้ interface เดียวกับ DonkiParser (BasePOParser)
3. คืนค่าเป็น ParsedPO object เหมือนกัน
4. สามารถเพิ่มใน Customer model ด้วย parser_key = "lopia_v1"

## Next Steps

1. เพิ่ม store code mappings ถ้ามีสาขาอื่นๆ ของ Lopia
2. เพิ่ม sample PDFs อื่นๆ สำหรับทดสอบ edge cases
3. อัพเดท `customers_config.json` ด้วยข้อมูลที่ถูกต้อง
4. สร้าง seed data file (`fixtures/seed_lopia.json`) ถ้าต้องการ

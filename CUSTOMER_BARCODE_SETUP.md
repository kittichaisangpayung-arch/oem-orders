# คู่มือการตั้งค่า Barcode แยกตาม Customer

## ภาพรวม

ระบบรองรับการใช้ barcode ที่แตกต่างกันสำหรับแต่ละ customer โดยใช้ระบบ **CustomerProduct** ซึ่งมีความยืดหยุ่นดังนี้:

- **Product.barcode** = barcode หลัก (default) ที่ใช้กับทุก customer
- **CustomerProduct.barcode_override** = barcode เฉพาะของแต่ละ customer (ถ้ามี)

## วิธีการตั้งค่า

### 1. เข้า Django Admin

ไปที่: https://terzanalak.pythonanywhere.com/admin/core/customerproduct/

### 2. เพิ่ม Customer-Specific Barcode

คลิก **Add Customer Product** แล้วกรอกข้อมูล:

- **Customer**: เลือก customer (เช่น Donki, Lopia)
- **Product**: เลือกสินค้า
- **Barcode override**: กรอก barcode เฉพาะของ customer นี้
- **Customer SKU**: (ถ้ามี) SKU ที่ customer ใช้
- **Min order qty override**: (ถ้าต้องการ) จำนวนสั่งขั้นต่ำเฉพาะ customer นี้
- **Sort rank override**: (ถ้าต้องการ) ลำดับการแสดงผลเฉพาะ customer นี้

### 3. ตัวอย่างการใช้งาน

#### กรณีที่ 1: Barcode เหมือนกันทุก Customer
ไม่ต้องสร้าง CustomerProduct เพียงตั้งค่า barcode ใน Product table เท่านั้น

#### กรณีที่ 2: Barcode ต่างกันตาม Customer

**สินค้า: Nama Pudding**
- Product.barcode = `4901234567890` (default)
- CustomerProduct (Donki).barcode_override = `4901234567890`
- CustomerProduct (Lopia).barcode_override = `8801234567899`

เมื่อ upload PO:
- PO จาก Donki ที่มี barcode `4901234567890` → จับคู่กับ Nama Pudding ✓
- PO จาก Lopia ที่มี barcode `8801234567899` → จับคู่กับ Nama Pudding ✓

## การทำงานของระบบ

เมื่อ upload PO ระบบจะค้นหาสินค้าตาม barcode ด้วยลำดับดังนี้:

1. **ค้นหาจาก CustomerProduct.barcode_override** ของ customer นั้นก่อน
2. ถ้าไม่เจอ → **ค้นหาจาก Product.barcode** (default)
3. ถ้ายังไม่เจอ → แจ้งเตือน unmapped barcode

## ข้อควรระวัง

1. **Barcode override ต้องไม่ซ้ำกันภายใน customer เดียวกัน**
   - ✓ Donki: Product A → barcode `111`, Product B → barcode `222`
   - ✗ Donki: Product A → barcode `111`, Product B → barcode `111` (ซ้ำ!)

2. **Barcode override สามารถซ้ำกันระหว่าง customer ได้**
   - ✓ Donki: Product A → barcode `111`
   - ✓ Lopia: Product B → barcode `111` (คนละ customer)

3. **ถ้าไม่กรอก barcode_override ระบบจะใช้ Product.barcode**

## ตรวจสอบการตั้งค่า

### ดูรายการ barcode ทั้งหมดของ customer

1. เข้า Django Admin → Customer Products
2. Filter by Customer
3. ดู column "Barcode override"

### ตรวจสอบว่า barcode ไหนยังไม่ได้ตั้งค่า

เมื่อ upload PO ระบบจะแจ้ง unmapped barcodes ที่ไม่สามารถจับคู่ได้

## การแก้ไขปัญหา

### ปัญหา: Upload PO แล้วได้ unmapped barcode

**แก้ไข:**
1. เช็คว่า barcode นั้นมีใน Product table หรือไม่
2. ถ้ามี → ใช้ barcode เดียวกันทุก customer (ไม่ต้องทำอะไร)
3. ถ้า customer นี้ใช้ barcode ต่างจากค่า default → สร้าง CustomerProduct พร้อม barcode_override

### ปัญหา: สินค้าจับคู่ผิด

**แก้ไข:**
1. ตรวจสอบว่ามี CustomerProduct ที่ซ้ำหรือไม่
2. ลบ CustomerProduct ที่ผิด
3. สร้างใหม่ด้วยข้อมูลที่ถูกต้อง

## เอกสารอ้างอิง

- Model: `apps/core/models.py` - `CustomerProduct`
- Logic: `apps/ingestion/services.py` - `_ingest_single_po()`
- Admin: `apps/core/admin.py` - `CustomerProductAdmin`

## การตั้งค่า Customer-Specific Barcode

ระบบรองรับการใช้ barcode ที่แตกต่างกันสำหรับแต่ละ customer แล้ว

### ✅ ฟีเจอร์ที่ใช้งานได้แล้ว

1. **Admin Panel** - จัดการ Customer Products
   - ไปที่: `/admin/core/customerproduct/`
   - เพิ่ม/แก้ไข barcode override สำหรับแต่ละ customer
   - แสดง "Effective Barcode" พร้อมบอกว่าเป็น override หรือ default

2. **PO Upload** - ระบบจับคู่ barcode อัตโนมัติ
   - ตรวจสอบ customer-specific barcode ก่อน
   - ถ้าไม่เจอค่อยใช้ default barcode
   - ไม่กระทบข้อมูลเก่า (backward compatible)

3. **Dashboard Views** - แสดงข้อมูลถูกต้องตาม customer
   - Production Summary
   - Store Matrix
   - Factory Summary
   - Shipping Summary
   - Delivery Notes

### 🎯 วิธีใช้งาน

#### 1. ตั้งค่า Customer Product
```
Admin → Core → Customer products → Add customer product

เลือก:
- Customer: ลูกค้าที่ต้องการ
- Product: สินค้าที่ต้องการกำหนด barcode
- Barcode override: barcode เฉพาะของลูกค้านี้ (เว้นว่าง = ใช้ default)
- Customer SKU: (optional) รหัสสินค้าที่ลูกค้าเรียก
- Min order qty override: (optional) MOQ เฉพาะลูกค้านี้
- Sort rank override: (optional) ลำดับแสดงผลเฉพาะลูกค้านี้
```

#### 2. Upload PO
```
เมื่อ upload PO file ระบบจะ:
1. อ่าน barcode จาก PO
2. หาใน CustomerProduct.barcode_override ของ customer นั้นก่อน
3. ถ้าไม่เจอ ค่อยหาใน Product.barcode (default)
4. จับคู่สินค้าอัตโนมัติ
```

#### 3. ดูรายงาน
```
Dashboard → เลือก Customer filter
- จะแสดงเฉพาะสินค้าที่มีใน PO
- ใช้ barcode ที่ถูกต้องตาม customer
```

### 📋 API / Utility Functions

สำหรับ developer ที่ต้องการใช้ในโค้ด:

```python
from apps.core.utils import (
    get_products_for_customer,
    get_barcode_to_product_map,
    find_product_by_barcode
)

# ดึง products ทั้งหมดสำหรับ customer พร้อม effective barcode
products = get_products_for_customer(customer)
# Returns: [{'product': Product, 'effective_barcode': '...', ...}]

# ดึง barcode mapping สำหรับ customer
barcode_map = get_barcode_to_product_map(customer)
# Returns: {'barcode': product_id, ...}

# หา product จาก barcode (รองรับ customer-specific)
product = find_product_by_barcode('8851234567890', customer)
# Returns: Product object or None
```

### 🔧 Model Methods

```python
# Get all products for a customer with effective values
products = CustomerProduct.get_products_for_customer(customer)

# Get effective barcode for a specific customer product
cp = CustomerProduct.objects.get(customer=customer, product=product)
barcode = cp.effective_barcode  # Returns override or default
moq = cp.effective_min_order_qty
rank = cp.effective_sort_rank
```

### ⚠️ หมายเหตุ

1. **Backward Compatible**: ถ้าไม่ได้ตั้งค่า CustomerProduct ระบบจะใช้ Product.barcode ปกติ
2. **Unique Constraint**: แต่ละ customer ต้องมี barcode override ไม่ซ้ำกัน
3. **Admin Search**: สามารถค้นหาด้วย barcode override, customer sku, หรือ product barcode
4. **Auto-complete**: Product field ใช้ autocomplete เพื่อความสะดวก

### 🚀 ตัวอย่างการใช้งาน

**สถานการณ์**: Donki และ Lopia ใช้ barcode ต่างกันสำหรับสินค้าชิ้นเดียวกัน

```
Product: Nama Pudding
- Default Barcode: 8851234567890

CustomerProduct (Donki):
- Barcode Override: 4901234567890
→ เมื่อ upload PO จาก Donki ที่มี barcode 4901234567890 จะจับคู่กับ Nama Pudding

CustomerProduct (Lopia):
- Barcode Override: 8851234500000
→ เมื่อ upload PO จาก Lopia ที่มี barcode 8851234500000 จะจับคู่กับ Nama Pudding

Customer อื่นๆ:
- ใช้ Default Barcode: 8851234567890
```

### 📊 Database Schema

```
CustomerProduct:
- customer_id (FK → Customer)
- product_id (FK → Product)
- barcode_override (CharField, optional)
- customer_sku (CharField, optional)
- min_order_qty_override (Integer, optional)
- sort_rank_override (Integer, optional)

Constraints:
- Unique(customer, product)
- Unique(customer, barcode_override) where barcode_override != ''
```

### 🔍 Troubleshooting

**Q: PO upload ไม่เจอสินค้า**
A: ตรวจสอบ:
1. CustomerProduct.barcode_override ตั้งค่าถูกต้องหรือไม่
2. Product.barcode มีอยู่หรือไม่ (fallback)
3. ดู PO line items ที่มี product = NULL

**Q: ต้องการให้แสดงเฉพาะ products ที่ customer มี barcode override**
A: ใช้ filter:
```python
CustomerProduct.objects.filter(customer=customer).exclude(barcode_override='')
```

**Q: ต้องการ bulk import CustomerProduct**
A: สร้าง CSV แล้วใช้ Django shell:
```python
import csv
from apps.core.models import Customer, Product, CustomerProduct

with open('customer_products.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        CustomerProduct.objects.update_or_create(
            customer_id=row['customer_id'],
            product_id=row['product_id'],
            defaults={
                'barcode_override': row['barcode_override'],
                'customer_sku': row.get('customer_sku', ''),
            }
        )
```

# สรุปการปรับปรุงระบบ Customer-Specific Barcode

## 🎯 สิ่งที่ทำเสร็จแล้ว

### 1. ปรับปรุง Model (apps/core/models.py)
- เพิ่ม method `get_products_for_customer()` ใน CustomerProduct
- ส่งคืนรายการสินค้าทั้งหมดพร้อม effective barcode สำหรับ customer
- รองรับการ sort ตาม effective_sort_rank และ effective_barcode

### 2. ปรับปรุง Admin (apps/core/admin.py)
- เพิ่มการแสดง "Effective Barcode" พร้อมสีเพื่อแยกระหว่าง override และ default
- เพิ่ม autocomplete สำหรับ Product field
- ปรับปรุง search fields และ list display

### 3. สร้าง Utility Functions (apps/core/utils.py)
- `get_products_for_customer(customer)` - ดึงรายการสินค้าทั้งหมดพร้อม effective values
- `get_barcode_to_product_map(customer)` - สร้าง mapping barcode → product_id
- `find_product_by_barcode(barcode, customer)` - หา product จาก barcode (รองรับ override)

### 4. PO Upload รองรับ Customer Barcode แล้ว (apps/ingestion/services.py)
- ตรวจสอบ CustomerProduct.barcode_override ก่อน
- ถ้าไม่เจอ ค่อยใช้ Product.barcode (default)
- Backward compatible กับข้อมูลเก่า

### 5. สร้างเอกสารคู่มือ (CUSTOMER_BARCODE_USAGE.md)
- คำแนะนำการใช้งาน
- ตัวอย่างการตั้งค่า
- API reference
- Troubleshooting guide

## 📝 วิธีใช้งาน

### สำหรับ Admin
1. ไปที่ `/admin/core/customerproduct/`
2. คลิก "Add customer product"
3. เลือก Customer และ Product
4. ใส่ Barcode override (barcode เฉพาะของ customer นี้)
5. บันทึก

### สำหรับระบบ
- เมื่อ upload PO ระบบจะจับคู่ barcode อัตโนมัติ
- Dashboard ทุกหน้าจะใช้ barcode ที่ถูกต้องตาม customer
- ไม่กระทบข้อมูลเก่า

## 🚀 การ Deploy บน PythonAnywhere

### Option 1: ใช้ Script อัตโนมัติ
```bash
cd ~/oem-orders
bash deploy_pythonanywhere.sh
```

### Option 2: รัน Manual (แนะนำ)
```bash
cd ~/oem-orders
git pull origin main

# ถ้ายังไม่ได้ติดตั้ง Pillow
pip install --user Pillow

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Collect static
python manage.py collectstatic --noinput

# Check
python manage.py check
```

### จากนั้น:
1. ไปที่ Web tab: https://www.pythonanywhere.com/user/terzanalak/webapps/
2. คลิก "Reload terzanalak.pythonanywhere.com"

## ✅ สิ่งที่ควรทดสอบหลัง Deploy

1. **Admin Panel**
   - เข้า `/admin/core/customerproduct/`
   - เพิ่ม customer product ใหม่
   - ตรวจสอบ autocomplete ทำงาน
   - ดู "Effective Barcode" แสดงผลถูกต้อง

2. **PO Upload**
   - Upload PO จาก customer ที่มี barcode override
   - ตรวจสอบว่าจับคู่สินค้าถูกต้อง
   - ดู POLineItem ว่ามี product_id ถูกต้อง

3. **Dashboard**
   - Production Summary: ดูว่าสินค้าแสดงถูกต้องตาม customer
   - Store Matrix: ตรวจสอบ quantities
   - Delivery Notes: สร้างและดูว่าใช้ barcode ถูกต้อง

## 🎯 ประโยชน์ของระบบใหม่

1. **แก้ปัญหา barcode ซ้ำกัน**
   - แต่ละ customer ใช้ barcode ของตัวเองได้
   - ไม่ต้องสร้าง Product ซ้ำ

2. **ยืดหยุ่น**
   - กำหนด MOQ แยกตาม customer
   - กำหนด sort order แยกตาม customer
   - เก็บ Customer SKU (รหัสที่ customer เรียก)

3. **Backward Compatible**
   - ถ้าไม่ได้ตั้งค่า override ระบบใช้ค่า default
   - ข้อมูลเก่าไม่กระทบ

4. **ใช้งานง่าย**
   - จัดการผ่าน Admin Panel
   - Upload PO ทำงานอัตโนมัติ
   - Dashboard แสดงผลถูกต้องทันที

## 📚 Files ที่เพิ่ม/แก้ไข

### เพิ่มใหม่
- `apps/core/utils.py` - Utility functions
- `CUSTOMER_BARCODE_USAGE.md` - คู่มือการใช้งาน
- `deploy_pythonanywhere.sh` - Script deploy
- `DEPLOYMENT_SUMMARY.md` - เอกสารนี้

### แก้ไข
- `apps/core/models.py` - เพิ่ม get_products_for_customer()
- `apps/core/admin.py` - ปรับปรุง CustomerProductAdmin
- `apps/ingestion/services.py` - รองรับ customer barcode แล้ว (ไม่ต้องแก้เพิ่ม)
- `apps/dashboard/views.py` - อัปเดตทุก view ให้แสดง customer-specific barcode:
  - `production_summary()` - แสดง barcode ตาม customer
  - `store_matrix()` - แสดง barcode ตาม customer
  - `factory_summary()` - แสดง barcode ตาม customer
  - `shipping_summary()` - แสดง barcode ตาม customer
  - `create_delivery_notes_from_batch()` - สร้าง delivery note ด้วย customer barcode

## 💡 Tips

### การ Bulk Import CustomerProduct
```python
# ใน Django shell
from apps.core.models import Customer, Product, CustomerProduct

# ตัวอย่าง: Donki ใช้ barcode ต่างจาก default
donki = Customer.objects.get(code='DONKI')
product = Product.objects.get(barcode='8851234567890')

CustomerProduct.objects.create(
    customer=donki,
    product=product,
    barcode_override='4901234567890',  # Donki's barcode
    customer_sku='DN-12345',  # Optional
)
```

### การดึงข้อมูล
```python
from apps.core.utils import get_products_for_customer

# ดึงสินค้าทั้งหมดของ customer
products = get_products_for_customer(customer)

for item in products:
    print(f"{item['product'].description}")
    print(f"  Barcode: {item['effective_barcode']}")
    print(f"  Has override: {item['has_override']}")
```

## ❓ คำถามที่พบบ่อย

**Q: ต้อง setup อะไรเพิ่มไหม?**
A: ไม่ต้อง ระบบพร้อมใช้งานทันที แค่ตั้งค่า CustomerProduct ใน Admin

**Q: ข้อมูลเก่าจะเสียไหม?**
A: ไม่เสีย ระบบ backward compatible 100%

**Q: ถ้าไม่ได้ตั้งค่า CustomerProduct จะเกิดอะไร?**
A: ระบบใช้ Product.barcode ปกติเหมือนเดิม

**Q: สามารถใช้ barcode override เดียวกันกับหลาย customer ได้ไหม?**
A: ได้ แต่ละ customer เป็นอิสระ (unique per customer)

**Q: จะหาว่า barcode ไหนยังไม่ได้ map ได้อย่างไร?**
A: ดูที่ POLineItem ที่มี product = NULL

---

## 🎉 สรุป

ระบบใหม่ช่วยให้:
- แต่ละ customer ใช้ barcode ของตัวเองได้
- จัดการง่ายผ่าน Admin Panel
- ทำงานอัตโนมัติเมื่อ upload PO
- ไม่กระทบข้อมูลเก่า

**พร้อม Deploy แล้ว!** 🚀

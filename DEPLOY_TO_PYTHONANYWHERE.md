# Deploy to PythonAnywhere - Customer Barcode Update

## ✅ สิ่งที่เสร็จแล้ว

ระบบรองรับ Customer-Specific Barcode ครบทุก view แล้ว:
- Production Summary
- Store Matrix (ตารางขนส่งสินค้า)
- Factory Summary
- Shipping Summary
- Create Delivery Notes

## 🚀 ขั้นตอน Deploy

### 1. เข้า PythonAnywhere Console
```
https://www.pythonanywhere.com/user/terzanalak/consoles/
```

### 2. ไปที่โปรเจค
```bash
cd ~/oem-orders
```

### 3. Pull code ล่าสุด
```bash
git pull origin main
```

### 4. Run migrations (ถ้ามี)
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Collect static files
```bash
python manage.py collectstatic --noinput
```

### 6. ไปที่ Web tab และ Reload
```
https://www.pythonanywhere.com/user/terzanalak/webapps/
คลิก "Reload terzanalak.pythonanywhere.com"
```

## 🧪 ทดสอบหลัง Deploy

### 1. ทดสอบ Lopia Batch 66
1. เข้า Dashboard → ตารางขนส่งสินค้า
2. เลือก Batch: 66
3. ควรแสดงเฉพาะ barcode ของ Lopia
4. ตรวจสอบว่า barcode แสดงถูกต้อง

### 2. ทดสอบ Production Summary
1. เข้า Dashboard → Production Summary
2. เลือก Customer filter
3. ตรวจสอบ barcode แสดงตาม customer ที่เลือก

### 3. ทดสอบ Delivery Note
1. สร้าง Delivery Note จาก batch ที่มี customer-specific barcode
2. ตรวจสอบว่า barcode ถูกต้อง

## 📋 Files ที่แก้ไข

- `apps/dashboard/views.py` - เพิ่ม customer barcode logic ใน 5 views
- `DEPLOYMENT_SUMMARY.md` - อัปเดตรายการ files ที่แก้ไข

## ⚠️ หมายเหตุ

- ไม่มี database migration ใหม่
- ระบบ backward compatible 100%
- ถ้าไม่มี CustomerProduct.barcode_override จะใช้ Product.barcode ปกติ

---
**พร้อม Deploy!** 🚀

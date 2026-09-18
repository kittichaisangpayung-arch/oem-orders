# คู่มือการย้ายไฟล์ PDF ไปยัง Google Cloud Storage

## ขั้นตอนที่ 1: เตรียมความพร้อม

### 1.1 ตรวจสอบว่าตั้งค่า GCS เรียบร้อยแล้ว

ตรวจสอบว่ามี environment variables เหล่านี้:

```bash
echo $USE_GCS
echo $GS_BUCKET_NAME
echo $GS_PROJECT_ID
echo $GOOGLE_APPLICATION_CREDENTIALS
```

ควรได้ค่าประมาณนี้:
```
True
oem-orders-media-thai
oem-orders
/home/username/gcs-credentials.json
```

### 1.2 ตรวจสอบว่า credentials file มีอยู่

```bash
ls -lh $GOOGLE_APPLICATION_CREDENTIALS
```

ควรเห็นไฟล์ JSON

---

## ขั้นตอนที่ 2: ทดสอบก่อน (Dry Run)

### 2.1 รัน Dry Run เพื่อดูว่าจะย้ายไฟล์อะไรบ้าง

```bash
cd ~/your_project_folder
source venv/bin/activate
python migrate_to_gcs.py --dry-run
```

**Dry Run จะแสดง:**
- จำนวนไฟล์ที่ต้องย้าย
- จำนวนไฟล์ที่อยู่บน GCS แล้ว
- ขนาดรวมของไฟล์ที่จะอัปโหลด
- ไฟล์ที่หายไป (ถ้ามี)

**ไม่มีการอัปโหลดจริง** - ปลอดภัย 100%

### ตัวอย่างผลลัพธ์:

```
======================================================================
PDF MIGRATION TO GOOGLE CLOUD STORAGE
======================================================================

📋 Configuration:
   USE_GCS: True
   Bucket: oem-orders-media-thai
   Dry Run: True
   Batch Size: 100

🔑 Connecting to Google Cloud Storage...
   ✅ Connected to bucket: oem-orders-media-thai

📦 Scanning Purchase Orders...
   Found 150 Purchase Orders with files

🔍 Checking which files need migration...

📊 Summary:
   ✅ Already on GCS: 0
   📤 Need to migrate: 145
   ❌ Missing files: 5

💾 Total size to migrate: 234.56 MB

🔍 DRY RUN - Files that would be migrated:
   1. PO #1: po_pdfs/1/order_001.pdf (123.4 KB)
   2. PO #2: po_pdfs/1/order_002.pdf (156.7 KB)
   ...

✅ Dry run complete. Run without --dry-run to actually migrate.
```

---

## ขั้นตอนที่ 3: Backup ไฟล์เดิม (แนะนำ)

```bash
cd ~/your_project_folder

# Backup media folder
tar -czf media_backup_$(date +%Y%m%d).tar.gz media/

# ดูขนาดไฟล์ backup
ls -lh media_backup_*.tar.gz

# ย้าย backup ไปที่อื่น (ถ้าต้องการ)
mv media_backup_*.tar.gz ~/backups/
```

---

## ขั้นตอนที่ 4: ย้ายไฟล์จริง

### 4.1 รันโปรแกรมย้ายไฟล์

```bash
cd ~/your_project_folder
source venv/bin/activate
python migrate_to_gcs.py
```

**จะถามยืนยัน 2 ครั้ง:**
1. ยืนยันว่าต้องการดำเนินการต่อ
2. ยืนยันก่อนเริ่มอัปโหลด

### 4.2 รอให้อัปโหลดเสร็จ

```
📤 Starting migration...
   [145/145] Uploading: po_pdfs/5/order_145.pdf...

======================================================================
MIGRATION COMPLETE
======================================================================
✅ Successfully migrated: 145 files
❌ Errors: 0 files
💾 Total uploaded: 234.56 MB
```

---

## ขั้นตอนที่ 5: ตรวจสอบว่าย้ายสำเร็จ

### 5.1 ตรวจสอบบน GCS Console

1. เปิด: https://console.cloud.google.com/storage/browser
2. เลือก bucket ของคุณ
3. ควรเห็นโฟลเดอร์ `po_pdfs/` พร้อมไฟล์

### 5.2 ทดสอบเปิดไฟล์จากระบบ

1. เข้าระบบ Django
2. ลองเปิด PO และดาวน์โหลด PDF
3. ตรวจสอบว่าไฟล์เปิดได้ปกติ

### 5.3 ตรวจสอบ URL ของไฟล์

```bash
cd ~/your_project_folder
python manage.py shell
```

```python
from apps.ingestion.models import PurchaseOrder

# เช็ค PO อันแรก
po = PurchaseOrder.objects.first()
print(po.source_file.url)

# ควรได้ URL แบบนี้:
# https://storage.googleapis.com/oem-orders-media-thai/po_pdfs/1/order_001.pdf
```

กด Ctrl+D เพื่อออกจาก shell

---

## ขั้นตอนที่ 6: ลบไฟล์เก่า (ประหยัด Storage)

### ⚠️ ทำเฉพาะเมื่อแน่ใจว่าไฟล์อัปโหลดสำเร็จแล้ว!

### 6.1 เช็คขนาดโฟลเดอร์ media

```bash
cd ~/your_project_folder
du -sh media/
```

### 6.2 ลบไฟล์ PDF เก่า

```bash
# ลบเฉพาะไฟล์ PDF
rm -rf media/po_pdfs/

# หรือลบทั้ง media folder (ถ้าไม่มีไฟล์อื่น)
rm -rf media/*
```

### 6.3 เช็ค Storage ที่เหลือ

```bash
du -sh ~
```

คุณควรเห็น storage ลดลงอย่างเห็นได้ชัด! 🎉

---

## การแก้ปัญหา

### ปัญหา: PermissionDenied

```
Error: 403 Permission Denied
```

**แก้ไข:**
1. ตรวจสอบว่า Service Account มี role `storage.objectAdmin`
2. ตรวจสอบว่า credentials file ถูกต้อง

```bash
cat $GOOGLE_APPLICATION_CREDENTIALS
```

### ปัญหา: BucketNotFound

```
Error: Bucket 'xxx' does not exist
```

**แก้ไข:**
1. ตรวจสอบชื่อ bucket:
```bash
echo $GS_BUCKET_NAME
```
2. ตรวจสอบว่า bucket สร้างแล้วใน GCS Console

### ปัญหา: google.cloud module not found

```
ModuleNotFoundError: No module named 'google.cloud'
```

**แก้ไข:**
```bash
pip install google-cloud-storage==2.14.0
```

### ปัญหา: อัปโหลดช้ามาก

- ปกติแล้วจะใช้เวลา 1-2 นาทีต่อ 100 ไฟล์
- ถ้าช้ากว่านี้ อาจเป็นปัญหาเน็ต
- สามารถกด Ctrl+C หยุดแล้วรันใหม่ได้ (จะข้ามไฟล์ที่อัปโหลดแล้ว)

### ปัญหา: อัปโหลดหยุดกลางคัน

รันใหม่:
```bash
python migrate_to_gcs.py
```

โปรแกรมจะข้ามไฟล์ที่อัปโหลดเรียบร้อยแล้วโดยอัตโนมัติ

---

## คำสั่งที่เป็นประโยชน์

### ดูจำนวนไฟล์ PDF

```bash
find media/po_pdfs -name "*.pdf" | wc -l
```

### ดูขนาดรวม

```bash
du -sh media/po_pdfs
```

### ดูไฟล์ที่ใหญ่ที่สุด 10 อันดับ

```bash
find media -type f -exec ls -lh {} \; | sort -k5 -rh | head -10
```

### Restore จาก Backup (ถ้าต้องการ)

```bash
cd ~/your_project_folder
tar -xzf media_backup_20260913.tar.gz
```

---

## สรุป

✅ ย้ายไฟล์ PDF จาก local ไปยัง GCS  
✅ ลบไฟล์เก่าเพื่อประหยัด storage  
✅ ไฟล์ใหม่จะถูกเก็บบน GCS โดยอัตโนมัติ  
✅ ไม่ต้องกังวลเรื่อง 500MB limit อีกต่อไป! 🎉

**จาก 446.9 MB → น่าจะเหลือประมาณ 100-200 MB** (ขึ้นกับขนาดไฟล์ PDF)

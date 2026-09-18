# 🚀 สรุปการติดตั้ง Google Cloud Storage สำหรับ PythonAnywhere

## 📁 ไฟล์ที่สร้างขึ้น

| ไฟล์ | คำอธิบาย |
|------|----------|
| `requirements.txt` | เพิ่ม django-storages และ google-cloud-storage |
| `oem_orders/settings.py` | เพิ่มการตั้งค่า GCS |
| `migrate_to_gcs.py` | โปรแกรมย้ายไฟล์ PDF ไป GCS |
| `verify_gcs.py` | ตรวจสอบว่าไฟล์อยู่บน GCS |
| `PYTHONANYWHERE_GCS_SETUP.md` | คู่มือตั้งค่า GCS บน PythonAnywhere |
| `MIGRATION_GUIDE.md` | คู่มือการย้ายไฟล์ |
| `check_disk_usage.md` | คู่มือเช็ค disk usage |

---

## 🎯 ขั้นตอนการทำงาน (5 ขั้นตอนหลัก)

### ✅ ขั้นตอนที่ 1: สร้าง Google Cloud Storage (10 นาที)

**ทำบนเครื่อง Local:**

1. สร้าง GCS Project: https://console.cloud.google.com/projectcreate
2. สร้าง Bucket: https://console.cloud.google.com/storage/create-bucket
   - ชื่อ: `oem-orders-media-thai`
   - Region: `asia-southeast1 (Singapore)`
3. สร้าง Service Account Key:

```bash
# เปิด Cloud Shell: https://console.cloud.google.com/
gcloud iam service-accounts create oem-orders-storage --display-name="OEM Orders Storage"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
    --member="serviceAccount:oem-orders-storage@$(gcloud config get-value project).iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud iam service-accounts keys create ~/gcs-key.json \
    --iam-account=oem-orders-storage@$(gcloud config get-value project).iam.gserviceaccount.com

cat ~/gcs-key.json
```

4. **คัดลอก JSON key ทั้งหมดไว้!**

📖 **คู่มือละเอียด:** `PYTHONANYWHERE_GCS_SETUP.md`

---

### ✅ ขั้นตอนที่ 2: Push Code ไป GitHub

**ทำบนเครื่อง Local:**

```bash
cd C:\Users\user\Desktop\PO_D

git add requirements.txt oem_orders/settings.py
git add migrate_to_gcs.py verify_gcs.py
git add *.md

git commit -m "Add Google Cloud Storage integration for PDF storage"

git push origin main
```

---

### ✅ ขั้นตอนที่ 3: ตั้งค่าบน PythonAnywhere (5 นาที)

**ทำบน PythonAnywhere:**

#### 3.1 อัปโหลด Credentials

1. ไปที่ **Files** tab
2. ไปที่ `/home/your_username/`
3. สร้างไฟล์: `gcs-credentials.json`
4. วาง JSON key ที่คัดลอกไว้
5. **Save**

#### 3.2 Pull Code ใหม่

```bash
cd ~/your_project_folder
git pull origin main
```

#### 3.3 ติดตั้ง Packages

```bash
source venv/bin/activate
pip install -r requirements.txt --no-cache-dir
```

#### 3.4 ตั้งค่า Environment Variables

1. ไปที่ **Web** tab
2. เลื่อนไปที่ **Environment variables**
3. เพิ่ม:

```
USE_GCS = True
GS_BUCKET_NAME = oem-orders-media-thai
GS_PROJECT_ID = oem-orders
GOOGLE_APPLICATION_CREDENTIALS = /home/your_username/gcs-credentials.json
```

**⚠️ แทนที่ `your_username` ด้วย username จริงของคุณ**

#### 3.5 Reload Web App

กดปุ่ม **Reload** (สีเขียว) ที่ด้านบน

---

### ✅ ขั้นตอนที่ 4: ย้ายไฟล์เก่าไป GCS (5-15 นาที)

**ทำบน PythonAnywhere Bash Console:**

#### 4.1 ทดสอบก่อน (Dry Run)

```bash
cd ~/your_project_folder
source venv/bin/activate
python migrate_to_gcs.py --dry-run
```

ดูว่าจะย้ายไฟล์อะไรบ้าง (ไม่มีการอัปโหลดจริง)

#### 4.2 Backup ก่อน

```bash
tar -czf media_backup_$(date +%Y%m%d).tar.gz media/
ls -lh media_backup_*.tar.gz
```

#### 4.3 ย้ายไฟล์จริง

```bash
python migrate_to_gcs.py
```

- กด `y` เพื่อยืนยัน
- รอให้อัปโหลดเสร็จ (1-2 นาทีต่อ 100 ไฟล์)

#### 4.4 ตรวจสอบความสำเร็จ

```bash
python verify_gcs.py
```

ตรวจสอบว่าไฟล์ทั้งหมดอยู่บน GCS

📖 **คู่มือละเอียด:** `MIGRATION_GUIDE.md`

---

### ✅ ขั้นตอนที่ 5: ลบไฟล์เก่า (ประหยัด Storage)

**⚠️ ทำเฉพาะเมื่อแน่ใจว่าไฟล์อยู่บน GCS แล้ว!**

```bash
# เช็คขนาดก่อนลบ
du -sh media/

# ลบไฟล์ PDF เก่า
rm -rf media/po_pdfs/

# เช็คขนาดหลังลบ
du -sh ~
```

**ผลลัพธ์:** Storage จะลดลงจาก **446.9 MB → ~100-200 MB** 🎉

---

## 🧪 การทดสอบ

### ทดสอบอัปโหลดไฟล์ใหม่

1. เข้าระบบ Django
2. อัปโหลด PO PDF ใหม่
3. ตรวจสอบใน GCS Console: https://console.cloud.google.com/storage/browser
4. ควรเห็นไฟล์ใน bucket `oem-orders-media-thai`

### ทดสอบดาวน์โหลดไฟล์

1. เปิด PO ที่มี PDF
2. คลิกดาวน์โหลด/ดู PDF
3. ไฟล์ควรเปิดได้ปกติ

### ตรวจสอบ URL ของไฟล์

```bash
python manage.py shell
```

```python
from apps.ingestion.models import PurchaseOrder
po = PurchaseOrder.objects.first()
print(po.source_file.url)
# ควะได้: https://storage.googleapis.com/oem-orders-media-thai/po_pdfs/...
```

---

## 📊 ผลลัพธ์ที่คาดหวัง

| ก่อน | หลัง |
|------|------|
| ไฟล์ PDF เก็บบน PythonAnywhere | ไฟล์ PDF เก็บบน GCS |
| Storage: 446.9 MB / 512 MB (87%) | Storage: ~100-200 MB / 512 MB (~20-40%) |
| มีปัญหา storage เต็ม | ไม่ต้องกังวลเรื่อง storage อีกต่อไป |
| ไฟล์เก่า: บน local | ไฟล์เก่า: ย้ายไป GCS |
| ไฟล์ใหม่: บน local | ไฟล์ใหม่: อัตโนมัติไป GCS |

---

## 🛠️ คำสั่งที่มีประโยชน์

### เช็ค Storage

```bash
# ดู storage ทั้งหมด
du -sh ~

# ดูแต่ละโฟลเดอร์
du -sh * | sort -h

# ดูไฟล์ที่ใหญ่ที่สุด
du -ah ~ | sort -rh | head -20
```

### เช็คว่า GCS ทำงาน

```bash
cd ~/your_project_folder
source venv/bin/activate

# ตรวจสอบ environment
python -c "import os; print('USE_GCS:', os.environ.get('USE_GCS')); print('BUCKET:', os.environ.get('GS_BUCKET_NAME'))"

# ตรวจสอบไฟล์
python verify_gcs.py
```

### ลบ Cache (ประหยัด Storage)

```bash
rm -rf ~/.cache/*
pip cache purge
```

📖 **คู่มือละเอียด:** `check_disk_usage.md`

---

## ❌ การแก้ปัญหา

### ปัญหา: Permission Denied

```bash
# เช็ค credentials file
cat $GOOGLE_APPLICATION_CREDENTIALS

# เช็คว่า Service Account มีสิทธิ์
# ไปที่: https://console.cloud.google.com/iam-admin/iam
# ควรเห็น oem-orders-storage@... มี role Storage Object Admin
```

### ปัญหา: Module not found

```bash
pip install --upgrade django-storages google-cloud-storage
```

### ปัญหา: 500 Error หลัง Reload

1. ไปที่ Web tab → Log files → Error log
2. ดู error message
3. มักเกิดจาก: credentials file path ผิด หรือ environment variables ไม่ถูกต้อง

---

## 💰 ค่าใช้จ่าย

- **ฟรี 5 GB** storage ต่อเดือน
- **ไม่ต้องใส่บัตรเครดิต** (ถ้าใช้ไม่เกิน 5GB)
- **Class A operations**: 5,000 ฟรีต่อเดือน
- **Class B operations**: 50,000 ฟรีต่อเดือน
- **Bandwidth**: 1 GB ฟรีต่อเดือน

เหมาะสำหรับ: ระบบขนาดเล็ก-กลางที่มีไฟล์ไม่เกิน 5GB

---

## 🎉 สรุป

### สิ่งที่ทำไปแล้ว:

✅ เพิ่ม django-storages และ google-cloud-storage  
✅ แก้ไข settings.py ให้รองรับ GCS  
✅ สร้างโปรแกรมย้ายไฟล์ (migrate_to_gcs.py)  
✅ สร้างโปรแกรมตรวจสอบ (verify_gcs.py)  
✅ สร้างคู่มือครบถ้วน  

### สิ่งที่คุณต้องทำ:

1. ⏳ สร้าง GCS Bucket และ Service Account (10 นาที)
2. ⏳ Push code ไป GitHub
3. ⏳ ตั้งค่าบน PythonAnywhere (5 นาที)
4. ⏳ ย้ายไฟล์เก่าไป GCS (5-15 นาที)
5. ⏳ ลบไฟล์เก่า (ประหยัด ~200-300 MB)

**รวมเวลา: ประมาณ 30-40 นาที**

### ประโยชน์:

🎯 ประหยัด storage บน PythonAnywhere  
🎯 ไม่ต้องกังวลเรื่อง 500MB limit  
🎯 ไฟล์ปลอดภัยบน Google Cloud  
🎯 เข้าถึงไฟล์ได้เร็วขึ้น (Google CDN)  
🎯 ฟรี! (ถ้าใช้ไม่เกิน 5GB)  

---

## 📞 ต้องการความช่วยเหลือ?

- อ่านคู่มือ: `PYTHONANYWHERE_GCS_SETUP.md`
- อ่านคู่มือการย้าย: `MIGRATION_GUIDE.md`
- ตรวจสอบ disk usage: `check_disk_usage.md`

**ขั้นตอนถัดไป:** สร้าง GCS Bucket ตามคู่มือ `PYTHONANYWHERE_GCS_SETUP.md` 🚀

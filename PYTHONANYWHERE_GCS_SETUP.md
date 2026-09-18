# การตั้งค่า Google Cloud Storage บน PythonAnywhere

## ขั้นตอนที่ 1: สร้าง Google Cloud Storage (ทำบนเครื่อง Local)

### 1.1 สร้าง Project และ Bucket
1. ไปที่ https://console.cloud.google.com/projectcreate
2. สร้าง project ชื่อ: `oem-orders`
3. เปิด Storage API: https://console.cloud.google.com/marketplace/product/google/storage-api
4. สร้าง Bucket:
   - ไปที่: https://console.cloud.google.com/storage/create-bucket
   - ชื่อ: `oem-orders-media-thai` (หรือชื่ออื่นที่ไม่ซ้ำ)
   - Location: **asia-southeast1 (Singapore)**
   - Storage class: **Standard**
   - Access control: **Uniform**

### 1.2 สร้าง Service Account และดาวน์โหลด Key

เปิด Cloud Shell และรันคำสั่งนี้:

```bash
# สร้าง Service Account
gcloud iam service-accounts create oem-orders-storage \
    --display-name="OEM Orders Storage"

# ให้สิทธิ์ Storage Admin
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
    --member="serviceAccount:oem-orders-storage@$(gcloud config get-value project).iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# สร้าง Key และดาวน์โหลด
gcloud iam service-accounts keys create ~/gcs-key.json \
    --iam-account=oem-orders-storage@$(gcloud config get-value project).iam.gserviceaccount.com

# แสดงเนื้อหา (คัดลอกทั้งหมด)
cat ~/gcs-key.json
```

**คัดลอก JSON key ทั้งหมดไว้!**

---

## ขั้นตอนที่ 2: ตั้งค่าบน PythonAnywhere

### 2.1 อัปโหลด Service Account Key

1. เข้า PythonAnywhere Dashboard
2. ไปที่แท็บ **Files**
3. ไปที่โฟลเดอร์: `/home/your_username/`
4. สร้างไฟล์ชื่อ: `gcs-credentials.json`
5. วาง JSON key ที่คัดลอกไว้ลงในไฟล์
6. **Save**

### 2.2 ตั้งค่า Environment Variables

1. ไปที่แท็บ **Web**
2. เลือก web app ของคุณ
3. เลื่อนลงไปที่ส่วน **Environment variables**
4. เพิ่ม environment variables ต่อไปนี้:

```
USE_GCS = True
GS_BUCKET_NAME = oem-orders-media-thai
GS_PROJECT_ID = oem-orders
GOOGLE_APPLICATION_CREDENTIALS = /home/your_username/gcs-credentials.json
```

**แทนที่:**
- `your_username` = username PythonAnywhere ของคุณ
- `oem-orders-media-thai` = ชื่อ bucket ที่สร้างไว้
- `oem-orders` = project ID ของคุณ

### 2.3 ติดตั้ง Dependencies

เปิด **Bash console** บน PythonAnywhere และรัน:

```bash
cd ~/your_project_folder
source venv/bin/activate
pip install django-storages[google]==1.14.2 google-cloud-storage==2.14.0
```

### 2.4 Reload Web App

1. กลับไปที่แท็บ **Web**
2. กดปุ่ม **Reload** (สีเขียว)

---

## ขั้นตอนที่ 3: ทดสอบ

### 3.1 ทดสอบอัปโหลดไฟล์
1. เข้าระบบและอัปโหลด PDF
2. ตรวจสอบว่าไฟล์ถูกเก็บใน GCS:
   - ไปที่ https://console.cloud.google.com/storage/browser
   - เลือก bucket ของคุณ
   - ควรเห็นโฟลเดอร์ `po_pdfs/`

### 3.2 ทดสอบดาวน์โหลดไฟล์
1. ลองเปิดไฟล์ PDF จากระบบ
2. ควรเปิดได้ปกติ

---

## การแก้ปัญหา

### ปัญหา: Permission Denied
- ตรวจสอบว่า Service Account มี role `roles/storage.objectAdmin`
- ตรวจสอบ path ของ `GOOGLE_APPLICATION_CREDENTIALS`

### ปัญหา: Bucket not found
- ตรวจสอบชื่อ bucket ใน `GS_BUCKET_NAME`
- ตรวจสอบว่า bucket สร้างแล้วใน GCS Console

### ปัญหา: Module not found
```bash
pip install --upgrade django-storages google-cloud-storage
```

### ดู Log บน PythonAnywhere
1. แท็บ **Web** → **Log files**
2. เปิด **Error log** เพื่อดู error messages

---

## ข้อมูลเพิ่มเติม

### ค่าใช้จ่าย
- **ฟรี 5GB** ต่อเดือน
- เหมาะสำหรับเก็บไฟล์ PDF

### Backup ไฟล์เดิม (ถ้ามี)
ถ้ามีไฟล์ใน `media/` อยู่แล้ว:

```bash
# บน PythonAnywhere Bash console
cd ~/your_project_folder
python manage.py shell

# ใน Django shell
from apps.ingestion.models import PurchaseOrder
from django.core.files.storage import default_storage

# อัปโหลดไฟล์เดิมไปยัง GCS
for po in PurchaseOrder.objects.all():
    if po.source_file:
        try:
            print(f"Uploading {po.source_file.name}...")
            # อัปโหลดจะเกิดขึ้นอัตโนมัติเมื่อเปิด USE_GCS
        except Exception as e:
            print(f"Error: {e}")
```

---

## สรุป

✅ ไฟล์ PDF จะถูกเก็บใน Google Cloud Storage  
✅ ประหยัดพื้นที่บน PythonAnywhere (500MB limit)  
✅ ไฟล์สามารถเข้าถึงได้จาก URL โดยตรง  
✅ ฟรี 5GB storage  

**หมายเหตุ:** ไฟล์เก่าที่เคยอัปโหลดจะยังอยู่ใน `media/` บนเซิร์ฟเวอร์ ไฟล์ใหม่ที่อัปโหลดหลังตั้งค่าจะไปที่ GCS

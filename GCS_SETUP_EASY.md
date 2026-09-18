# คู่มือติดตั้ง Google Cloud Storage แบบง่าย (5-10 นาที)

## ขั้นตอนที่ 1: สร้าง Project และเปิด API (3 นาที)

1. เปิด: https://console.cloud.google.com/projectcreate
2. Project name: `oem-orders`
3. คลิก **CREATE**
4. รอ project สร้างเสร็จ (30 วินาที)
5. เปิด: https://console.cloud.google.com/marketplace/product/google/storage-api
6. คลิก **ENABLE** (ถ้ายังไม่ enable)

## ขั้นตอนที่ 2: สร้าง Storage Bucket (2 นาที)

1. เปิด: https://console.cloud.google.com/storage/create-bucket
2. Bucket name: `oem-orders-media-thai` (หรือชื่ออื่นที่ไม่ซ้ำ)
3. Location type: **Region**
4. Location: **asia-southeast1 (Singapore)** - ใกล้ไทยสุด
5. Storage class: **Standard**
6. Access control: **Uniform**
7. คลิก **CREATE**

**จดชื่อ bucket ไว้!** เช่น: `oem-orders-media-thai`

## ขั้นตอนที่ 3: สร้าง Service Account และ Key (2 นาที)

**วิธีง่าย - ใช้ Cloud Shell:**

1. เปิด: https://console.cloud.google.com/
2. คลิกที่ไอคอน **Cloud Shell** มุมขวาบน (>_)
3. คัดลอกคำสั่งนี้ทั้งหมด แล้ววางใน Cloud Shell:

```bash
# สร้าง Service Account
gcloud iam service-accounts create oem-orders-storage \
    --display-name="OEM Orders Storage"

# ให้สิทธิ์ Storage Admin
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
    --member="serviceAccount:oem-orders-storage@$(gcloud config get-value project).iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# สร้าง Key
gcloud iam service-accounts keys create ~/oem-orders-key.json \
    --iam-account=oem-orders-storage@$(gcloud config get-value project).iam.gserviceaccount.com

# แสดงเนื้อหาไฟล์
cat ~/oem-orders-key.json
```

4. กด **Enter**
5. **คัดลอกเนื้อหา JSON ทั้งหมด** ที่แสดงออกมา (ตั้งแต่ `{` ถึง `}`)

## ขั้นตอนที่ 4: บอกผลให้ผมรู้

บอกผมว่า:
1. ชื่อ bucket ที่สร้าง: `_________________`
2. ได้ JSON key แล้ว: ✅ หรือ ❌

แล้วผมจะติดตั้งโค้ดให้เสร็จทันที!

---

## หมายเหตุ

- ฟรี 5GB storage
- ไม่ต้องใส่บัตรเครดิต (ถ้าใช้ไม่เกิน 5GB)
- Service Account Key คือ JSON file ที่เก็บเป็นความลับ
- ใช้เวลารวมประมาณ 5-10 นาที

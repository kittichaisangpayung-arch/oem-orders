# Google Cloud Storage Setup Guide

## ขั้นตอนการตั้งค่า Google Cloud Storage

### 1. สร้าง Google Cloud Project

1. ไปที่ [Google Cloud Console](https://console.cloud.google.com/)
2. สร้าง Project ใหม่ หรือเลือก Project ที่มีอยู่
3. จดชื่อ Project ID ไว้

### 2. เปิดใช้งาน Google Cloud Storage API

1. ไปที่ [APIs & Services](https://console.cloud.google.com/apis/library)
2. ค้นหา "Cloud Storage API"
3. คลิก "Enable"

### 3. สร้าง Storage Bucket

1. ไปที่ [Cloud Storage](https://console.cloud.google.com/storage)
2. คลิก "Create Bucket"
3. ตั้งค่า:
   - **Bucket name**: เช่น `oem-orders-media` (ต้องไม่ซ้ำกับใครในโลก)
   - **Location type**: Region (เลือก `asia-southeast1` - Singapore ใกล้ไทย)
   - **Storage class**: Standard
   - **Access control**: Fine-grained
   - **Public access**: อนุญาต public access (เพื่อให้ดูไฟล์ได้)
4. คลิก "Create"

### 4. ตั้งค่า Permissions

1. เลือก bucket ที่สร้าง
2. ไปที่ tab "Permissions"
3. คลิก "Grant Access"
4. เพิ่ม:
   - **Principal**: `allUsers`
   - **Role**: Storage Object Viewer
5. คลิก "Save"

### 5. สร้าง Service Account

1. ไปที่ [Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. คลิก "Create Service Account"
3. ตั้งค่า:
   - **Service account name**: `oem-orders-storage`
   - **Description**: "Service account for OEM Orders media files"
4. คลิก "Create and Continue"
5. เพิ่ม Role: `Storage Object Admin`
6. คลิก "Continue" → "Done"

### 6. สร้าง JSON Key

1. คลิกที่ Service Account ที่สร้าง
2. ไปที่ tab "Keys"
3. คลิก "Add Key" → "Create new key"
4. เลือก "JSON"
5. คลิก "Create" → ไฟล์ JSON จะถูกดาวน์โหลด
6. **เก็บไฟล์นี้ไว้ปลอดภัย!**

### 7. ตั้งค่าบน PythonAnywhere

#### วิธีที่ 1: ใช้ Environment Variables (แนะนำ)

เปิด Bash console บน PythonAnywhere:

```bash
cd ~/oem-orders
nano .env
```

เพิ่มข้อมูลนี้:

```bash
# Google Cloud Storage
GCS_BUCKET_NAME=oem-orders-media
GCS_PROJECT_ID=your-project-id
GCS_CREDENTIALS_JSON='{"type":"service_account","project_id":"your-project-id",...}'
```

**หมายเหตุ**: สำหรับ `GCS_CREDENTIALS_JSON` ให้คัดลอกเนื้อหาทั้งหมดจากไฟล์ JSON ที่ดาวน์โหลดมาใส่ในเครื่องหมาย `'...'`

จากนั้นแก้ไข WSGI file (`/var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py`):

```python
import os
import sys

# Load environment variables from .env file
from pathlib import Path
env_file = Path('/home/YOUR_USERNAME/oem-orders/.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value.strip('\'"')

path = '/home/YOUR_USERNAME/oem-orders'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'oem_orders.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

#### วิธีที่ 2: ตั้งค่าใน WSGI file โดยตรง

แก้ไข WSGI file:

```python
import os
import sys
import json

path = '/home/YOUR_USERNAME/oem-orders'
if path not in sys.path:
    sys.path.append(path)

# Google Cloud Storage credentials
os.environ['GCS_BUCKET_NAME'] = 'oem-orders-media'
os.environ['GCS_PROJECT_ID'] = 'your-project-id'
os.environ['GCS_CREDENTIALS_JSON'] = json.dumps({
    "type": "service_account",
    "project_id": "your-project-id",
    "private_key_id": "...",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
    "client_email": "...",
    "client_id": "...",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "..."
})

os.environ['DJANGO_SETTINGS_MODULE'] = 'oem_orders.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 8. ติดตั้ง Dependencies บน PythonAnywhere

```bash
cd ~/oem-orders
source ~/.virtualenvs/oem-orders/bin/activate
pip install django-storages[google] google-cloud-storage
```

### 9. ทดสอบ

```bash
python manage.py shell
```

```python
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

# ทดสอบอัพโหลดไฟล์
content = ContentFile(b'Hello from GCS!')
path = default_storage.save('test.txt', content)
print(f'File saved to: {path}')
print(f'File URL: {default_storage.url(path)}')

# ทดสอบอ่านไฟล์
file_content = default_storage.open(path).read()
print(f'Content: {file_content}')

# ลบไฟล์ทดสอบ
default_storage.delete(path)
print('Test file deleted')
```

### 10. Reload Web App

ไปที่ Web tab → คลิก "Reload"

## ทดสอบการทำงาน

1. อัพโหลด PDF ผ่านระบบ
2. ตรวจสอบที่ [Cloud Storage Console](https://console.cloud.google.com/storage) จะเห็นไฟล์ใน bucket
3. คลิกที่ไฟล์ จะได้ URL แบบ: `https://storage.googleapis.com/oem-orders-media/po_pdfs/...`

## ข้อดี

✅ **ฟรี 5GB** (พอเก็บไฟล์ PDF หลายพันไฟล์)  
✅ ไฟล์เข้าถึงได้จาก URL โดยตรง  
✅ ไม่กินพื้นที่ PythonAnywhere  
✅ Backup อัตโนมัติ  
✅ CDN รองรับทั่วโลก  

## หมายเหตุ

- ไฟล์เก่าที่อยู่ใน `media/` บน PythonAnywhere จะยังคงอยู่
- ไฟล์ใหม่ที่อัพโหลดหลังจากตั้งค่าจะเก็บบน GCS
- ถ้าไม่ตั้งค่า GCS ระบบจะใช้ local storage ตามเดิม

## Free Tier Limits

- **Storage**: 5GB
- **Class A operations**: 5,000 operations/month (upload, list)
- **Class B operations**: 50,000 operations/month (download, read)
- **Network egress**: 1GB/month to Australia and China, 100GB/month to other regions

น่าจะพอใช้งานได้นานครับ!

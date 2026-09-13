# Google Drive Setup Guide

## ขั้นตอนการตั้งค่า Google Drive สำหรับเก็บไฟล์ PDF

### 1. สร้าง Google Cloud Project (ฟรี)

1. ไปที่ [Google Cloud Console](https://console.cloud.google.com/)
2. คลิก "Select a project" → "New Project"
3. ตั้งชื่อ Project: `oem-orders` (หรือชื่ออื่นที่ชอบ)
4. คลิก "Create"

### 2. เปิดใช้งาน Google Drive API

1. เลือก Project ที่สร้าง
2. ไปที่ [APIs & Services > Library](https://console.cloud.google.com/apis/library)
3. ค้นหา "Google Drive API"
4. คลิก "Enable"

### 3. สร้าง OAuth 2.0 Credentials

#### 3.1 ตั้งค่า OAuth Consent Screen

1. ไปที่ [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)
2. เลือก "External" → คลิก "Create"
3. กรอกข้อมูล:
   - **App name**: `OEM Orders`
   - **User support email**: อีเมลของคุณ
   - **Developer contact information**: อีเมลของคุณ
4. คลิก "Save and Continue"
5. ส่วน "Scopes": คลิก "Add or Remove Scopes"
   - เลือก `.../auth/drive.file` หรือ `.../auth/drive`
   - คลิก "Update" → "Save and Continue"
6. ส่วน "Test users": คลิก "Add Users"
   - เพิ่มอีเมล Google ของคุณ
   - คลิก "Save and Continue"
7. คลิก "Back to Dashboard"

#### 3.2 สร้าง OAuth Client ID

1. ไปที่ [Credentials](https://console.cloud.google.com/apis/credentials)
2. คลิก "Create Credentials" → "OAuth client ID"
3. เลือก Application type: "Desktop app"
4. ตั้งชื่อ: `OEM Orders Desktop`
5. คลิก "Create"
6. **ดาวน์โหลดไฟล์ JSON** → จะได้ไฟล์ชื่อประมาณ `client_secret_xxx.json`
7. คลิก "OK"

### 4. สร้างโฟลเดอร์บน Google Drive

1. ไปที่ [Google Drive](https://drive.google.com/)
2. สร้างโฟลเดอร์ใหม่: "OEM Orders Media"
3. เปิดโฟลเดอร์ → คลิก "Share" → ตั้งเป็น "Anyone with the link can view"
4. ดูที่ URL: `https://drive.google.com/drive/folders/XXXXXXXXXXXXX`
5. **จด Folder ID** (ตัวอักษรหลัง `/folders/`)

### 5. ตั้งค่าบน PythonAnywhere

#### 5.1 อัพโหลด client_secret JSON

1. เปิด "Files" tab บน PythonAnywhere
2. ไปที่ `/home/YOUR_USERNAME/oem-orders/`
3. อัพโหลดไฟล์ `client_secret_xxx.json` → เปลี่ยนชื่อเป็น `client_secrets.json`

#### 5.2 ตั้งค่า Environment Variables

แก้ไข WSGI file (`/var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py`):

```python
import os
import sys
import json

path = '/home/YOUR_USERNAME/oem-orders'
if path not in sys.path:
    sys.path.append(path)

# Google Drive configuration
os.environ['GDRIVE_FOLDER_ID'] = 'YOUR_FOLDER_ID_HERE'

# Load client_secrets.json
with open('/home/YOUR_USERNAME/oem-orders/client_secrets.json', 'r') as f:
    client_config = json.load(f)
    os.environ['GDRIVE_CREDENTIALS_JSON'] = json.dumps(client_config)

os.environ['DJANGO_SETTINGS_MODULE'] = 'oem_orders.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**แทนที่:**
- `YOUR_USERNAME` → username PythonAnywhere ของคุณ
- `YOUR_FOLDER_ID_HERE` → Folder ID จาก Google Drive

#### 5.3 ติดตั้ง Dependencies

เปิด Bash console:

```bash
cd ~/oem-orders
git pull origin main
source ~/.virtualenvs/oem-orders/bin/activate
pip install -r requirements.txt
```

### 6. Authenticate Google Drive (ครั้งแรก)

**วิธีนี้ต้องทำบนเครื่องคุณก่อน แล้วอัพโหลด credentials.json ขึ้น PythonAnywhere**

#### 6.1 บนเครื่องคุณ (Local)

```bash
cd C:\Users\user\Desktop\PO_D
python
```

```python
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# Authenticate
gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # เปิด browser ให้ login
gauth.SaveCredentialsFile("credentials.json")

print("Authentication successful!")
print("credentials.json has been created")
```

Browser จะเปิดขึ้นมา:
1. เลือกบัญชี Google ของคุณ
2. คลิก "Continue" (จะขึ้นว่า "Google hasn't verified this app" ไม่เป็นไร)
3. คลิก "Continue" อีกครั้ง
4. อนุญาตให้เข้าถึง Google Drive
5. เสร็จแล้วจะได้ไฟล์ `credentials.json`

#### 6.2 อัพโหลด credentials.json ไป PythonAnywhere

1. เปิด "Files" tab บน PythonAnywhere
2. ไปที่ `/home/YOUR_USERNAME/oem-orders/`
3. อัพโหลดไฟล์ `credentials.json`

### 7. Reload Web App

ไปที่ Web tab → คลิก "Reload"

### 8. ทดสอบ

อัพโหลด PDF ผ่านระบบ → ตรวจสอบที่ Google Drive จะเห็นโฟลเดอร์และไฟล์ถูกสร้างขึ้นโดยอัตโนมัติ

## โครงสร้างโฟลเดอร์บน Google Drive

```
OEM Orders Media/
├── po_pdfs/
│   ├── 1/              → batch #1
│   │   ├── file1.pdf
│   │   └── file2.pdf
│   ├── 2/              → batch #2
│   └── ...
├── products/           → รูปภาพสินค้า
└── company/            → โลโก้บริษัท
```

## วิธีดู URL ของไฟล์

ไฟล์จะมี URL แบบ:
```
https://drive.google.com/uc?export=view&id=FILE_ID
```

Django จะ generate URL นี้อัตโนมัติเมื่อเรียกใช้ `file.url`

## ข้อดี

✅ **ฟรี 15GB** (มากกว่า GCS 3 เท่า!)  
✅ ไม่กินพื้นที่ PythonAnywhere  
✅ Backup อัตโนมัติ  
✅ เข้าถึงง่ายผ่าน Google Drive  
✅ จัดการไฟล์ได้ตรงๆ บน Drive  

## ข้อจำกัด

⚠️ ต้อง authenticate ครั้งแรก (ทำครั้งเดียว)  
⚠️ ช้ากว่า GCS เล็กน้อย  
⚠️ มี API quota limits (750 requests/user/100 seconds)  

## Troubleshooting

### ถ้า authentication หมดอายุ

ระบบจะ refresh token อัตโนมัติ แต่ถ้าเกิดปัญหา:

```bash
# บน PythonAnywhere
cd ~/oem-orders
rm credentials.json
```

จากนั้นทำ Step 6 ใหม่

### ถ้าไฟล์อัพโหลดไม่ขึ้น

ตรวจสอบ error log:
```bash
tail -f /var/log/YOUR_USERNAME.pythonanywhere.com.error.log
```

### ถ้า Quota เกิน

Google Drive API มี limit:
- **Queries per day**: 1,000,000,000
- **Queries per 100 seconds per user**: 1,000
- **Queries per 100 seconds**: 10,000

น่าจะพอใช้งานปกติไม่มีปัญหาครับ

## หมายเหตุ

- ไฟล์เก่าบน `media/` (local) จะยังคงอยู่
- ไฟล์ใหม่จะเก็บบน Google Drive
- ถ้าไม่ตั้งค่า ระบบจะใช้ local storage ตามเดิม
- ไฟล์ `gdrive_mapping.json` จะถูกสร้างเพื่อเก็บ mapping ของ file path → Google Drive file ID

## Security

🔒 **สำคัญ**: 
- ไฟล์ `client_secrets.json` และ `credentials.json` ต้อง**เก็บเป็นความลับ**
- อย่า commit ไฟล์เหล่านี้ขึ้น GitHub
- ได้เพิ่มไว้ใน `.gitignore` แล้ว

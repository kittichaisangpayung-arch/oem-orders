# คู่มือติดตั้ง Google Drive สำหรับ PythonAnywhere

## ข้อมูลที่มีอยู่แล้ว
- ✅ Folder ID: `1nHxNzRASn0i-WjpZ7DAvXMruNSfumNo7`
- ✅ credentials.json อยู่ในโฟลเดอร์ Google Drive แล้ว

---

## ขั้นตอนการติดตั้ง

### 1. ดาวน์โหลด credentials.json จาก Google Drive
- เข้าไปที่ https://drive.google.com/drive/folders/1nHxNzRASn0i-WjpZ7DAvXMruNSfumNo7
- ดาวน์โหลดไฟล์ `credentials.json` มาไว้ที่เครื่อง

### 2. อัพเดทโค้ดบน PythonAnywhere

เปิด Bash console:
```bash
cd ~/oem-orders
git pull origin main
```

### 3. ติดตั้ง Dependencies

```bash
source ~/.virtualenvs/oem-orders/bin/activate
pip install -r requirements.txt
```

### 4. อัพโหลดไฟล์ credentials.json

ผ่าน Files tab:
- ไปที่ `/home/YOUR_USERNAME/oem-orders/`
- อัพโหลดไฟล์ `credentials.json` ที่ดาวน์โหลดมา

### 5. แก้ไข WSGI File

ไปที่ Web tab → คลิกที่ WSGI configuration file

แทนที่เนื้อหาทั้งหมดด้วย:

```python
import os
import sys

path = '/home/YOUR_USERNAME/oem-orders'
if path not in sys.path:
    sys.path.append(path)

# Google Drive configuration
os.environ['GDRIVE_FOLDER_ID'] = '1nHxNzRASn0i-WjpZ7DAvXMruNSfumNo7'

os.environ['DJANGO_SETTINGS_MODULE'] = 'oem_orders.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**แทนที่ `YOUR_USERNAME`** ด้วย username PythonAnywhere ของคุณ

### 6. Reload Web App

ไปที่ Web tab → คลิกปุ่ม **"Reload"** สีเขียว

---

## ทดสอบ

1. อัพโหลด PDF ผ่านระบบ
2. ตรวจสอบที่ Google Drive: https://drive.google.com/drive/folders/1nHxNzRASn0i-WjpZ7DAvXMruNSfumNo7
3. จะเห็นโครงสร้างโฟลเดอร์:
   ```
   po_pdfs/
   └── 2569/
       └── กันยายน/
           └── สัปดาห์ที่ 2/
               └── 1/
                   └── your-file.pdf
   ```

---

## หมายเหตุ

- ระบบจะสร้างโฟลเดอร์ตามโครงสร้าง **ปี/เดือน/สัปดาห์/batch_id** อัตโนมัติ
- ปีใช้ พ.ศ. (เช่น 2569)
- เดือนเป็นภาษาไทย (เช่น กันยายน)
- สัปดาห์คำนวณจากวันที่ในเดือน (1-7 = สัปดาห์ที่ 1, 8-14 = สัปดาห์ที่ 2, ฯลฯ)

---

## Troubleshooting

### ถ้า error: "No module named 'pydrive2'"
```bash
pip install PyDrive2 PyYAML
```

### ถ้า error เกี่ยวกับ authentication
- ตรวจสอบว่าไฟล์ `credentials.json` อยู่ที่ `/home/YOUR_USERNAME/oem-orders/credentials.json`
- ตรวจสอบว่าไฟล์ไม่เสียหาย (เปิดดูได้ไหม)

### ดู Error Logs
```bash
tail -f /var/log/YOUR_USERNAME.pythonanywhere.com.error.log
```

# ขั้นตอนการ Deploy ไป PythonAnywhere (แก้ปัญหา Error 500)

## 1. Commit และ Push โค้ดใหม่

```bash
git add -A
git commit -m "Fix file upload error 500 on PythonAnywhere - add error handling and fallback to local storage"
git push origin main
```

## 2. ไปที่ PythonAnywhere Console

เข้า Bash console บน PythonAnywhere แล้วรันคำสั่ง:

```bash
# ไปยังโฟลเดอร์โปรเจค
cd ~/your-project-folder

# Pull โค้ดใหม่
git pull origin main

# Install dependencies ใหม่
pip install -r requirements.txt --user

# สร้างโฟลเดอร์ media (ถ้ายังไม่มี)
mkdir -p media/company
mkdir -p media/products
chmod -R 755 media
```

## 3. ตั้งค่า Environment Variables

ไปที่ **Web tab → Environment variables** บน PythonAnywhere:

### ตัวเลือก A: ใช้ Local Storage (แนะนำ - ง่ายที่สุด)
**ลบหรือไม่ต้องตั้งค่า:**
- `GDRIVE_FOLDER_ID`
- `GDRIVE_CREDENTIALS_JSON`

### ตัวเลือก B: ใช้ Google Drive (ถ้าต้องการ)
**ตั้งค่า:**
- `GDRIVE_FOLDER_ID` = `your-google-drive-folder-id`
- `GDRIVE_CREDENTIALS_JSON` = ไม่ต้องตั้ง (ใช้ไฟล์ credentials.json แทน)

จากนั้นอัพโหลด `credentials.json` ไปยัง project folder บน PythonAnywhere

## 4. ตั้งค่า Static Files Mapping

ไปที่ **Web tab → Static files** บน PythonAnywhere:

เพิ่ม mapping:
```
URL: /media/
Directory: /home/yourusername/your-project-folder/media
```

## 5. Reload Web App

ไปที่ **Web tab** → คลิกปุ่ม **"Reload"** สีเขียว

## 6. ทดสอบ

1. ไปที่ `/admin/` บน PythonAnywhere
2. เข้า **Company Profile**
3. แก้ไข record
4. **อัพโหลดรูป logo**
5. คลิก Save

**✅ ถ้าไม่มี error 500 = สำเร็จ!**

## 7. ถ้ายังมีปัญหา - ดู Error Log

ไปที่ **Web tab** → คลิก **"Error log"**

จะเห็น error message ที่บอกว่าปัญหาเกิดจากอะไร

---

## สิ่งที่แก้ไข

✅ เพิ่ม error handling ใน Google Drive storage
✅ เพิ่ม error message ที่อ่านง่ายใน admin
✅ แก้ MEDIA_URL จาก `'media/'` เป็น `'/media/'`
✅ แก้ urls.py ให้ serve media files ใน production
✅ เพิ่ม django-admin-sortable2 สำหรับ drag & drop sorting

---

## หมายเหตุ

- **Local storage** = รูปจะเก็บบน PythonAnywhere server
- **Google Drive** = รูปจะเก็บบน Google Drive (ซับซ้อนกว่า)
- แนะนำใช้ **Local storage** สำหรับ PythonAnywhere เพราะง่ายกว่า

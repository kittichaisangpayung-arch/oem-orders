# แก้ปัญหา Error 500 ตอนอัพโหลดรูป Company Profile บน PythonAnywhere

## สาเหตุ
- Google Drive storage ล้มเหลวเพราะ credentials ไม่ถูกต้องหรือ authentication ล้มเหลว
- Media files ไม่ถูก serve ในโหมด production

## วิธีแก้ (เลือก 1 วิธี)

### วิธีที่ 1: ใช้ Local Storage (แนะนำสำหรับ PythonAnywhere)

1. **ไปที่ PythonAnywhere Web tab → Environment variables**
   - **ลบ** หรือตั้งค่าว่าง: `GDRIVE_FOLDER_ID`
   - **ลบ** หรือตั้งค่าว่าง: `GDRIVE_CREDENTIALS_JSON`

2. **สร้างโฟลเดอร์ media**
   ```bash
   cd ~/your-project-path
   mkdir -p media/company
   chmod 755 media
   chmod 755 media/company
   ```

3. **Reload web app** จาก PythonAnywhere Web tab

4. **ทดสอบอัพโหลดรูป** - ควรทำงานปกติแล้ว

---

### วิธีที่ 2: แก้ไข Google Drive Credentials (ถ้าต้องการใช้ Google Drive)

1. **เช็ค credentials.json บน PythonAnywhere**
   ```bash
   cd ~/your-project-path
   cat credentials.json
   ```
   
2. **ถ้าไฟล์ไม่มีหรือผิด - สร้างใหม่:**
   - ไปที่ [Google Cloud Console](https://console.cloud.google.com/)
   - สร้าง Service Account และ download credentials.json
   - Upload ไฟล์ขึ้น PythonAnywhere

3. **ตั้งค่า Environment Variables บน PythonAnywhere:**
   ```
   GDRIVE_FOLDER_ID=your-folder-id-here
   GDRIVE_CREDENTIALS_JSON=/home/yourusername/yourproject/credentials.json
   ```

4. **ตั้งค่า permissions**
   ```bash
   chmod 600 credentials.json
   ```

5. **Reload web app**

---

## ตรวจสอบว่าแก้สำเร็จ

1. ไปที่ Django Admin → Company Profile
2. แก้ไข record
3. อัพโหลดรูป logo
4. บันทึก
5. **ถ้าไม่มี error 500 = แก้สำเร็จ**

---

## ดู Error Log (ถ้ายังมีปัญหา)

บน PythonAnywhere:
- ไปที่ Web tab
- คลิก "Error log" เพื่อดู error ที่เกิดขึ้น
- จะบอกว่า error เกิดจากอะไรแน่ชัด

---

## Note
- ไฟล์ทั้งหมดถูกแก้แล้วใน code ของคุณ
- อย่าลืม **git push** แล้ว **git pull** บน PythonAnywhere
- อย่าลืม **Reload** web app หลังแก้ไข

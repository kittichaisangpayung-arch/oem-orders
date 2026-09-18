# วิธีเช็คว่าอะไรกิน Storage บน PythonAnywhere

## คำสั่งเช็คขนาดไฟล์ (รันบน PythonAnywhere Bash Console)

### 1. เช็คขนาดแต่ละโฟลเดอร์หลัก
```bash
cd ~
du -sh * .* 2>/dev/null | sort -h
```

### 2. เช็คโฟลเดอร์โปรเจค
```bash
cd ~/your_project_folder
du -sh * 2>/dev/null | sort -h
```

### 3. เช็คโฟลเดอร์ media (ไฟล์ PDF)
```bash
cd ~/your_project_folder
du -sh media/*
find media -type f -exec ls -lh {} \; | awk '{print $5 "\t" $9}' | sort -h
```

### 4. เช็คขนาด Virtual Environment
```bash
du -sh ~/your_project_folder/venv
```

### 5. เช็คขนาด Database
```bash
ls -lh ~/your_project_folder/db.sqlite3
```

### 6. เช็คโฟลเดอร์ที่ใหญ่ที่สุด 10 อันดับแรก
```bash
cd ~
du -ah . 2>/dev/null | sort -rh | head -20
```

---

## สิ่งที่มักกิน Storage

### 1. **Virtual Environment (venv)** - ~100-300 MB
- จำเป็นต้องมี ลบไม่ได้

### 2. **Media Files (PDF)** - ขึ้นกับจำนวนไฟล์
```bash
# นับจำนวนไฟล์ PDF
find ~/your_project_folder/media -name "*.pdf" | wc -l

# เช็คขนาดรวม
du -sh ~/your_project_folder/media
```

### 3. **Database (db.sqlite3)** - อาจใหญ่ถ้ามีข้อมูลเยอะ
```bash
ls -lh ~/your_project_folder/db.sqlite3
```

### 4. **Log Files** - บางทีใหญ่มาก
```bash
# เช็ค log files
ls -lh ~/.local/share/virtualenvs/*/pip*.log 2>/dev/null
find ~ -name "*.log" -exec ls -lh {} \;
```

### 5. **Cache Files**
```bash
du -sh ~/.cache
```

---

## วิธีลดขนาด Storage

### 1. ลบ Cache (ปลอดภัย)
```bash
rm -rf ~/.cache/*
pip cache purge
```

### 2. ลบ Log Files เก่า (ปลอดภัย)
```bash
find ~ -name "*.log" -type f -delete
```

### 3. Clean pip cache
```bash
pip cache purge
```

### 4. ลบ Static Files ที่ไม่จำเป็น (ถ้ามี)
```bash
cd ~/your_project_folder
rm -rf staticfiles_build
```

### 5. **ย้าย Media Files ไป GCS (แนะนำ!)**
หลังตั้งค่า GCS เสร็จแล้ว สามารถลบไฟล์เก่าได้:

```bash
# Backup ก่อน (ถ้ายังไม่ได้อัปโหลดไป GCS)
cd ~/your_project_folder
tar -czf media_backup.tar.gz media/

# ลบไฟล์ media เก่า (หลังอัปโหลดไป GCS แล้ว)
rm -rf media/po_pdfs/*
```

### 6. ลด Virtual Environment (ระวัง!)
```bash
# สร้าง venv ใหม่ที่เบากว่า
cd ~/your_project_folder
rm -rf venv
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --no-cache-dir
```

---

## คำสั่งเช็คอย่างรวดเร็ว

รันคำสั่งนี้เพื่อดูภาพรวม:

```bash
echo "=== TOP 15 LARGEST FILES/FOLDERS ==="
du -ah ~ 2>/dev/null | sort -rh | head -15

echo -e "\n=== VIRTUAL ENV SIZE ==="
du -sh ~/*/venv 2>/dev/null

echo -e "\n=== MEDIA FILES SIZE ==="
du -sh ~/*/media 2>/dev/null

echo -e "\n=== DATABASE SIZE ==="
find ~ -name "db.sqlite3" -exec ls -lh {} \;

echo -e "\n=== CACHE SIZE ==="
du -sh ~/.cache

echo -e "\n=== TOTAL USAGE ==="
du -sh ~
```

---

## แนะนำ

1. **เช็คก่อน**: รันคำสั่งด้านบนเพื่อดูว่าอะไรกิน storage มากที่สุด
2. **ลบ cache**: ลบ cache ก่อนเสมอ (ปลอดภัย)
3. **GCS**: ตั้งค่า GCS แล้วย้ายไฟล์ PDF ไป
4. **Backup**: Backup ก่อนลบไฟล์สำคัญ

หลังตั้งค่า GCS เสร็จ คุณจะมี storage เหลือเยอะขึ้นเพราะไฟล์ PDF ใหม่จะไม่ถูกเก็บบนเซิร์ฟเวอร์ PythonAnywhere อีกต่อไป 🎉

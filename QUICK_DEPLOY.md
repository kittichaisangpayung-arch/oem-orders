# 🚀 Quick Deploy to PythonAnywhere

## วิธีที่ 1: One-Command Deploy (แนะนำ)

SSH เข้า PythonAnywhere console แล้วรันคำสั่งเดียว:

```bash
bash <(curl -s https://raw.githubusercontent.com/kittichaisangpayung-arch/oem-orders/main/deploy.sh)
```

หรือ:

```bash
wget -O - https://raw.githubusercontent.com/kittichaisangpayung-arch/oem-orders/main/deploy.sh | bash
```

---

## วิธีที่ 2: Manual Deploy

```bash
# 1. Clone repository
cd ~
git clone https://github.com/kittichaisangpayung-arch/oem-orders.git
cd oem-orders

# 2. Run deployment script
chmod +x deploy.sh
./deploy.sh
```

---

## หลังจาก Deploy เสร็จ

### 1. คัดลอก WSGI Configuration

```bash
cat ~/oem-orders/wsgi_config_*.py
```

คัดลอกเนื้อหาทั้งหมด แล้วไปที่:
- PythonAnywhere Web tab
- คลิก "WSGI configuration file"
- ลบเนื้อหาเดิมทั้งหมด
- วางเนื้อหาที่คัดลอกมา
- Save

### 2. ตั้งค่า Static Files

ใน Web tab → Static files section:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/YOUR_USERNAME/oem-orders/staticfiles/` |
| `/media/` | `/home/YOUR_USERNAME/oem-orders/media/` |

### 3. Reload Web App

คลิกปุ่ม **Reload** สีเขียวใน Web tab

### 4. เข้าใช้งาน

`https://YOUR_USERNAME.pythonanywhere.com`

---

## สร้าง Superuser (ถ้าต้องการ)

```bash
cd ~/oem-orders
source venv/bin/activate
python manage.py createsuperuser
```

---

## Update ครั้งต่อไป

```bash
~/oem-orders/update.sh
```

จากนั้น Reload web app ใน PythonAnywhere dashboard

---

## คำสั่งที่ใช้บ่อย

```bash
# เข้า Django shell
cd ~/oem-orders && source venv/bin/activate && python manage.py shell

# ดู logs
tail -f /var/log/YOUR_USERNAME.pythonanywhere.com.error.log

# Test Lopia parser
cd ~/oem-orders && source venv/bin/activate
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.parsers.registry import get_parser
parser = get_parser('lopia_v1')
print('Lopia parser loaded successfully!')
"
```

---

## Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'django'"
```bash
cd ~/oem-orders
source venv/bin/activate
pip install -r requirements.txt
```

### ❌ "WSGI file not found"
ตรวจสอบว่าคัดลอก WSGI configuration ถูกต้อง และ reload web app แล้ว

### ❌ "Static files not loading"
```bash
cd ~/oem-orders
source venv/bin/activate
python manage.py collectstatic --noinput
```
จากนั้นตรวจสอบ Static files path ใน Web tab

### ❌ "502 Bad Gateway"
ตรวจสอบ error log:
```bash
tail -100 /var/log/YOUR_USERNAME.pythonanywhere.com.error.log
```

---

## ✅ Checklist

- [ ] Run deployment script
- [ ] Copy WSGI configuration
- [ ] Set static files path
- [ ] Reload web app
- [ ] Test website
- [ ] Create superuser (optional)
- [ ] Test admin panel
- [ ] Test Lopia parser

---

**🎉 เสร็จแล้ว! ระบบพร้อมใช้งาน**

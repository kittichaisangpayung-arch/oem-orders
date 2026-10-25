# OEM Orders (PO Dashboard)

ระบบ Django 4.2 สำหรับรับ PO (PDF) จากลูกค้า → ทำ Delivery Note / Invoice / Quotation / Claims
ผู้ใช้สื่อสารภาษาไทย ตอบเป็นภาษาไทย

## แผนที่โค้ด

- `apps/parsers/` แยก PDF PO ต่อลูกค้า: `donki.py` (`donki_v1`), `lopia.py` (`lopia_v1`), `registry.py` ใช้เลือก parser ตาม `Customer.parser_key`
- `apps/ingestion/` อัปโหลด PO: `services.py` (`ingest_batch`) แปลงผล parser เป็น `PurchaseOrderBatch` → `PurchaseOrder` → `POLineItem` (มี `line_no` ตามลำดับใน PDF) และมี manual entry ใน `views.py`
- `apps/core/` master data: `Customer`, `Store`, `Product` (`sort_rank`, `min_order_qty`, `product_group`), `CustomerProduct` (`barcode_override`), `CompanyProfile`; `access.py` = เช็กกลุ่มผู้ใช้
- `apps/dashboard/` งานหลักเกือบทั้งหมดอยู่ใน `views.py` (~2500 บรรทัด ให้ grep หาชื่อฟังก์ชันแทนการอ่านทั้งไฟล์):
  - `production_summary`, `store_matrix` (+ override/claim inline), `factory_summary`, `shipping_summary`
  - Delivery Note: `create_delivery_notes_from_batch` (เรียงสินค้าตาม PO line order ของแต่ละสาขา), `delivery_note_detail` (พิมพ์ 5 รายการ/หน้า)
  - `export_flowaccount_playwright` สร้างไฟล์ Playwright `.spec.ts` สำหรับ FlowAccount (ชื่อลูกค้าใน `FLOWACCOUNT_CUSTOMER_NAMES`)
  - Invoice / billing statement / receipt / Quotation
  - ไฟล์แยก: `product_trends.py`, `product_inactivity.py`, `claim_analytics.py`, `compensation_analytics.py`
  - models: `DeliveryNote`/`DeliveryNoteItem`, `Invoice`/`InvoiceLineItem`, `Quotation`/`QuotationLineItem`, `StoreProductOverride`
- `apps/claims/`, `apps/manage_data/` (CRUD ลูกค้า/สาขา/สินค้า), `apps/accounts/` (`seed_roles`)
- `templates/<app>/` HTML templates; เอกสารพิมพ์อยู่ที่ `templates/dashboard/*_detail.html`
- `oem_orders/settings.py`: SQLite ในเครื่อง, ใช้ `DATABASE_URL` ถ้ามี, ใช้ Google Drive storage เมื่อตั้ง `GDRIVE_*`

## คำสั่ง

```bash
venv/Scripts/python manage.py runserver
venv/Scripts/python -m pytest apps/dashboard/tests --nomigrations -q
```

- ต้องใช้ `venv/Scripts/python` (Python ของระบบไม่มี pytest-django)
- ต้องใส่ `--nomigrations` เพราะ migration `0014_merge_20260927_1223` ของ dashboard ไม่อยู่ใน repo
- มี 3 test ที่ fail อยู่ก่อนแล้ว: 2 test ใน `test_production_claims.py` และ `test_store_matrix_claim_adds_to_qty_before_min_order_bump`

## Deploy (PythonAnywhere: terzanalak.pythonanywhere.com)

1. commit แล้ว push ขึ้น `main` (https://github.com/kittichaisangpayung-arch/oem-orders)
2. บน PythonAnywhere: `cd ~/oem-orders && git pull origin main`
3. ถ้ามี migration ใหม่ให้รัน `python manage.py migrate` ถ้าแก้ static ให้รัน `collectstatic`
4. กด Reload ที่แท็บ Web

`FRAME_ANCESTORS` (ใช้ฝังหน้า trends ใน iframe) อยู่ในไฟล์ WSGI บนเซิร์ฟเวอร์ ไม่ได้อยู่ใน repo

## ข้อควรระวัง

- ห้าม commit `credentials.json`, `client_secrets.json`, `db.sqlite3` (อยู่ใน `.gitignore` แล้ว)
- ไฟล์ `.md` อื่นที่ root เป็นบันทึกเก่าและอาจล้าสมัย ให้ยึดไฟล์นี้เป็นหลัก

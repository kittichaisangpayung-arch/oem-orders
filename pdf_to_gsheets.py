import pdfplumber
import pandas as pd
import re
import os
import glob
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from concurrent.futures import ProcessPoolExecutor, as_completed
import threading
import logging
from datetime import date

# pip install gspread google-auth google-auth-oauthlib google-api-python-client
import gspread
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json

with open("barcode_description.json", "r", encoding="utf-8") as f:
    BARCODE_DESC = json.load(f)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Config — แก้ค่าเหล่านี้
# -----------------------------------------------------------------------
CREDENTIALS_FILE = "credentials.json"   # path ไปยังไฟล์ credentials ที่ดาวน์โหลดจาก Google Cloud
SPREADSHEET_NAME = "Order donki Weekly  New New"  # ชื่อ Google Sheet (ต้องตรงทุกตัวอักษร)
WORKSHEET_NAME   = "Sheet1"             # ชื่อ sheet tab ที่จะเขียนข้อมูล
SHEET10_NAME     = "Sheet10"            # ชื่อ sheet tab ที่จะเขียนข้อมูล (ปรับยอดตามขั้นต่ำแล้ว)

# โฟลเดอร์หลักบน Google Drive ที่จะเก็บ PDF (ปี > เดือน > สัปดาห์)
# ดึงมาจาก URL: https://drive.google.com/drive/folders/1nHxNzRASn0i-WjpZ7DAvXMruNSfumNo7
DRIVE_PARENT_FOLDER_ID = "1nHxNzRASn0i-WjpZ7DAvXMruNSfumNo7"

# --- Drive ใช้ OAuth ของบัญชี Gmail ส่วนตัว (ไม่ใช้ Service Account) ---
# เหตุผล: Service Account มี storage quota = 0 บน Gmail ส่วนตัว ทำให้อัพโหลดไฟล์ไม่ได้
# (จะเจอ error "storageQuotaExceeded") ต้องให้ไฟล์ที่อัพโหลดนับเป็นพื้นที่ของบัญชีคนจริงแทน
# ไฟล์ oauth_client_secret.json ดาวน์โหลดจาก Google Cloud Console > APIs & Services
# > Credentials > Create Credentials > OAuth client ID > Desktop app
OAUTH_CLIENT_SECRET_FILE = "oauth_client_secret.json"
OAUTH_TOKEN_FILE = "drive_token.json"   # ไฟล์ token ที่จะถูกสร้างอัตโนมัติหลัง login ครั้งแรก
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

THAI_MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

# ขั้นต่ำการสั่งต่อ Barcode
MIN_ORDER_MAP = {
    '2800000011086': 0,
    '2800000010355': 10,
    '2800000010379': 10,
    '2800000010362': 10,
    '2800000010386': 10,
    '2800000010584': 10,
    '2800000010577': 10,
    '2800000010393': 50,
    '2800000010409': 30,
    '2800000010607': 30,
    '2800000010591': 30,
    '2800000011260': 100,
    '2800000011277': 10,
    '2800000011390': 100,
    '2800000011574': 100,
    '2800000011598':30,
    '2800000011604':30,
    '2800000011581':30
}

# mapping Store Code → ชื่อ header ใน Sheet2 (PO)
STORE_CODE_MAP = {
    '7001': 'Donki Thonglor',
    '7004': 'MBK Center',
    '7006': 'J-park Sriracha',
    '7003': 'Seacon Square',
    '7007': 'Thaniya Plaza',
    '7005': 'Seacon Bangkae',
    '7008': 'Fashion Island',
    '7010': 'Central WestGate',
}

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# --- จับคู่ใบ Invoice (มีเลข INV) กับแถวใน PO Summary แล้วอัพเดทคอลัมน์ File Name ---
PO_SUMMARY_SHEET_NAME = "PO Summary"
# ยอมรับส่วนต่างของยอดเงินได้ไม่เกินกี่บาท (กันปัดเศษ) ตอนเทียบ Total Amount
AMOUNT_MATCH_TOLERANCE = 1.0
# ใช้ยอด "รวมเป็นเงิน" (ก่อน VAT) ของใบ invoice เทียบกับ Total Amount ใน PO Summary
# (ถ้าอยากเทียบยอดรวม VAT แทน ให้เปลี่ยนเป็น "grandtotal" แทน "subtotal" ตรงจุดที่ใช้งาน)
INVOICE_AMOUNT_FIELD = "subtotal"

# เดาจากคำว่า "สาขา ..." ในใบ invoice -> ชื่อสาขาให้ตรงกับ STORE_CODE_MAP
# ใช้แบบ "substring อยู่ในบรรทัดสาขา" ไม่ใช่ exact match เพราะ vendor เขียนไม่คงที่
# (บางทีใช้ชื่อสาขา บางทีใช้ชื่อถนน เช่น "ศรีนครินทร์" แทน "ซีคอนสแควร์")
BRANCH_KEYWORD_MAP = {
    "ศรีราชา": "J-park Sriracha",
    "ทองหล่อ": "Donki Thonglor",
    "เอ็มบีเค": "MBK Center",
    "สยาม": "MBK Center",
    "ศรีนครินทร์": "Seacon Square",
    "ซีคอนสแควร์": "Seacon Square",
    "ธนิยะ": "Thaniya Plaza",
    "บางแค": "Seacon Bangkae",
    "แฟชั่น": "Fashion Island",
    "เวสเกต": "Central WestGate",
}

# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------
PREDEFINED_ORDER = [
    '2800000011086', '2800000010355', '2800000010379', '2800000010362',
    '2800000010386', '2800000010584', '2800000010577', '2800000010393',
    '2800000010409', '2800000010607', '2800000010591', '2800000011260',
    '2800000011277', '2800000011390', '2800000011574','2800000011598',
    '2800000011604','2800000011581'
]
BARCODE_RANK = {b: i for i, b in enumerate(PREDEFINED_ORDER)}
COLUMNS = ['Store Code', 'Store Name', 'Order No.', 'Barcode', 'Description', 'UOM', 'Qty', 'Qty2', 'Amount', 'Total Amount']

# -----------------------------------------------------------------------
# Regex (compiled once)
# -----------------------------------------------------------------------
_RE_STORE    = re.compile(r"Store Name\s+([^\n]+?)(?:\s+Vendor Name|$)", re.MULTILINE)
_RE_STORE_CODE = re.compile(r"Store Code\s+(\S+)")
_RE_ORDER_NO   = re.compile(r"Order No\.\s+(\S+)")

# regex "หลัก" — ใช้ได้กับ PDF ที่มีคอลัมน์ UOM ชัดเจน (เช่น PCS, BOX)
_RE_PRODUCTS = re.compile(
    r"(\d{13})\s+([A-Za-z0-9 ]+?)\s+([A-Z]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d,\.]+)"
)
# regex "สำรอง" (flexible) — ใช้กับ PDF ที่ไม่มีคอลัมน์ UOM ระบุไว้ (บางเวนเดอร์เว้นว่าง)
_RE_FLEX = re.compile(
    r"(\d{13})\s+(.+?)\s+(\d+)\s+(\d+)\s+\d+\s+([\d,\.]+)\s+\w+\s+\w+\s+([\d,\.]+)"
)
# ใช้เพื่อ "นับจำนวนแถวสินค้าที่ควรเจอจริง" — เอาไว้ตรวจสอบว่า regex หลัก/สำรอง
# ดึงข้อมูลมาได้ครบหรือไม่ (นับเฉพาะบาร์โค้ดที่อยู่ต้นบรรทัด เพื่อไม่ปนกับเลข VAT No./
# Vendor Code ที่บางครั้งมี 13 หลักเหมือนกันแต่ไม่ใช่บาร์โค้ดสินค้า)
_RE_ROW_BARCODE = re.compile(r"(?m)^(\d{13})\b")

# --- regex สำหรับใบกำกับภาษี/invoice ของ vendor (เช่น Boxa) ที่มีเลข INV ---
_RE_INVOICE_NO       = re.compile(r"เลขที่\s+(INV\S+)")
_RE_INVOICE_SUBTOTAL = re.compile(r"รวมเป็นเงิน\s+([\d,]+\.\d{2})")
_RE_INVOICE_GRANDTOTAL = re.compile(r"จำนวนเงินรวมทั้งสิ้น\s+([\d,]+\.\d{2})")
# นับจำนวนรวม: จับแค่ "<จำนวน> Bottle" เท่านั้น ไม่ยึดคอลัมน์ถัดไป เพราะบางใบ invoice
# มีคอลัมน์ ภาษี/หัก ณ ที่จ่าย แทรกอยู่ก่อนคอลัมน์มูลค่า ทำให้รูปแบบแถวไม่คงที่
# (ยอดเงินรวมใช้จาก "รวมเป็นเงิน" ด้านบนอยู่แล้ว ไม่ต้องพึ่งการ sum รายบรรทัด)
_RE_INVOICE_ITEM_ROW = re.compile(r"(\d+)\s+Bottle\b")
# จับข้อความทั้งบรรทัดหลัง "สาขา" (ไม่ใช่แค่คำแรก) เพราะบางสาขาเขียนชื่อหลายคำ
# เช่น "สาขา เซ็นทรัล เวสเกต" หรือใช้ชื่อถนนแทนชื่อสาขา เช่น "สาขา ศรีนครินทร์"
_RE_INVOICE_BRANCH   = re.compile(r"สาขา\s*[:\s]*([^\n]+)")


# -----------------------------------------------------------------------
# Extraction
# -----------------------------------------------------------------------
def _parse_store_name(text: str) -> str:
    m = _RE_STORE.search(text)
    return m.group(1).strip() if m else "Unknown Store"

def _parse_store_code(text: str) -> str:
    m = _RE_STORE_CODE.search(text)
    return m.group(1).strip() if m else "Unknown"

def _parse_order_no(text: str) -> str:
    m = _RE_ORDER_NO.search(text)
    return m.group(1).strip() if m else "Unknown"

def _to_float(val: str) -> float:
    try:
        return float(val.replace(',', ''))
    except ValueError:
        return 0.0

def extract_store_data(text: str) -> pd.DataFrame:
    store_code = _parse_store_code(text)
    store_name = _parse_store_name(text)
    order_no   = _parse_order_no(text)
    rows = []
    for barcode, desc, uom, qty, qty2, _, amount in _RE_PRODUCTS.findall(text):
        qty2_int = int(qty2)
        amt = _to_float(amount)
        rows.append([store_code, store_name, order_no, barcode, desc.strip(), uom,
                     int(qty), qty2_int, amt, int(qty2_int * amt)])
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(rows, columns=COLUMNS)

def extract_store_data_flexible(text: str) -> pd.DataFrame:
    store_code = _parse_store_code(text)
    store_name = _parse_store_name(text)
    order_no   = _parse_order_no(text)
    rows = []
    for barcode, desc, qty, qty2, amount, total in _RE_FLEX.findall(text):
        rows.append([store_code, store_name, order_no, barcode, desc.strip(), "PCS",
                     int(qty), int(qty2), _to_float(amount), int(_to_float(total))])
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(rows, columns=COLUMNS)

def _read_single_pdf(pdf_path: str) -> pd.DataFrame | None:
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t
        if not text.strip():
            logger.warning("ไม่มีข้อความ: %s", os.path.basename(pdf_path))
            return None

        # จำนวนแถวสินค้าที่ "ควร" เจอจริงในไฟล์นี้ (ใช้เทียบว่า parse ได้ครบหรือยัง)
        expected_rows = len(set(_RE_ROW_BARCODE.findall(text)))

        df = extract_store_data(text)

        # เดิม: เช็คแค่ df.empty ทำให้กรณีที่ regex หลักดึงมาได้ "บางส่วน" (เช่น PDF
        # ที่ไม่มีคอลัมน์ UOM ระบุ แล้วบังเอิญมีคำตัวพิมพ์ใหญ่ในชื่อสินค้าทำให้ regex
        # จับผิดเป็น UOM) จะไม่ fallback ไปใช้ flexible เลย ทำให้ข้อมูลหายไปเงียบๆ
        # แก้ไข: เทียบจำนวนแถวที่ได้กับจำนวนบาร์โค้ดที่ควรเจอจริง แล้วเลือกวิธีที่ได้ครบกว่า
        if df.empty or len(df) < expected_rows:
            df_flex = extract_store_data_flexible(text)
            if len(df_flex) > len(df):
                logger.info(
                    "↪️ ใช้ flexible regex แทน: %s (regex หลักได้ %d/%d แถว, flexible ได้ %d แถว)",
                    os.path.basename(pdf_path), len(df), expected_rows, len(df_flex)
                )
                df = df_flex

        if len(df) < expected_rows:
            logger.warning(
                "⚠️ ดึงข้อมูลได้ไม่ครบ: %s (ได้ %d จากที่ควรมี %d แถว — ตรวจสอบรูปแบบ PDF)",
                os.path.basename(pdf_path), len(df), expected_rows
            )

        return df if not df.empty else None
    except Exception as exc:
        logger.error("อ่านไม่สำเร็จ: %s | %s", os.path.basename(pdf_path), exc)
        return None

def read_multiple_pdfs(pdf_folder: str, progress_cb=None):
    pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"ไม่พบไฟล์ PDF ในโฟลเดอร์: {pdf_folder}")

    results = []
    max_workers = min(os.cpu_count() or 4, len(pdf_files), 8)
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_read_single_pdf, p): p for p in pdf_files}
        for done, future in enumerate(as_completed(futures), 1):
            df = future.result()
            if df is not None:
                results.append(df)
            if progress_cb:
                progress_cb(done, len(pdf_files))

    if not results:
        raise ValueError("ไม่สามารถอ่านข้อมูลจาก PDF ใดๆ ได้")

    final_df = pd.concat(results, ignore_index=True)[COLUMNS]
    total_by_store = (final_df.groupby('Store Name', sort=True)['Total Amount']
                               .sum().reset_index())
    return final_df, total_by_store, final_df['Total Amount'].sum()


# -----------------------------------------------------------------------
# จับคู่ใบ Invoice (Boxa เป็นต้น) กับแถวใน PO Summary
# -----------------------------------------------------------------------
def _extract_invoice_info(pdf_path: str) -> dict:
    """
    ดึงข้อมูลจากใบ invoice ของ vendor (มีเลข INV) — ใช้เฉพาะ 2 หน้าแรกเท่านั้น
    (หน้า 1 = ตารางสินค้า, หน้า 2 = ยอดรวม/สาขา/ลายเซ็น คือเอกสาร "ต้นฉบับ" ตัวจริง)
    ไม่อ่านหน้าที่เหลือ เพราะไฟล์ประเภทนี้มักมี "สำเนา" ซ้ำต่อท้ายอีก 2 หน้า
    ถ้ารวมทุกหน้าจะได้จำนวน/ยอดเงินซ้ำสองเท่า
    ใบที่มีรายการสินค้าเยอะ ตารางจะเต็มพอดีหน้า 1 ทำให้ยอดรวมถูกดันไปอยู่หน้า 2
    แทน จึงต้องอ่านทั้งสองหน้ารวมกัน อ่านหน้าเดียวไม่พอ
    """
    with pdfplumber.open(pdf_path) as pdf:
        pages_to_read = pdf.pages[:2]  # หน้า 1-2 เท่านั้น (ต้นฉบับ ไม่รวมสำเนา)
        first_page_text = "\n".join(p.extract_text() or "" for p in pages_to_read)

    inv_match = _RE_INVOICE_NO.search(first_page_text)
    inv_no = inv_match.group(1).strip() if inv_match else None

    subtotal_match = _RE_INVOICE_SUBTOTAL.search(first_page_text)
    subtotal = _to_float(subtotal_match.group(1)) if subtotal_match else None

    grandtotal_match = _RE_INVOICE_GRANDTOTAL.search(first_page_text)
    grandtotal = _to_float(grandtotal_match.group(1)) if grandtotal_match else None

    qty_total = sum(int(q) for q in _RE_INVOICE_ITEM_ROW.findall(first_page_text))

    branch_match = _RE_INVOICE_BRANCH.search(first_page_text)
    branch_line = branch_match.group(1).strip() if branch_match else None
    store_hint = None
    if branch_line:
        for keyword, store_name in BRANCH_KEYWORD_MAP.items():
            if keyword in branch_line:
                store_hint = store_name
                break

    return {
        "file_path": pdf_path,
        "file_name": os.path.basename(pdf_path),
        "inv_no": inv_no,
        "subtotal": subtotal,
        "grandtotal": grandtotal,
        "qty_total": qty_total,
        "store_hint": store_hint,
        "branch_keyword": branch_line,
    }


def match_invoices_to_po_summary(invoice_folder: str, status_cb=None):
    """
    อ่านใบ invoice ของ vendor ทั้งหมดในโฟลเดอร์ที่เลือก จับคู่กับแถวใน Sheet
    'PO Summary' โดยเทียบ Total Items (จำนวน bottle รวม) + Total Amount
    (ใช้ INVOICE_AMOUNT_FIELD เป็นยอดอ้างอิง) แล้วอัพเดทคอลัมน์ 'File Name'
    ของแถวที่ match เจอ ให้เป็นเลข INV แทนชื่อไฟล์เดิม

    คืนค่า: (matched, unmatched, ambiguous) — แต่ละอันเป็น list ของ dict อธิบายผลลัพธ์
    """
    def _status(msg):
        logger.info(msg)
        if status_cb:
            status_cb(msg)

    invoice_files = glob.glob(os.path.join(invoice_folder, "*.pdf"))
    if not invoice_files:
        raise FileNotFoundError(f"ไม่พบไฟล์ PDF ในโฟลเดอร์: {invoice_folder}")

    _status("🔐 กำลังเชื่อมต่อ Google Sheets...")
    client = get_gsheet_client()
    spreadsheet = client.open(SPREADSHEET_NAME)

    try:
        ws = spreadsheet.worksheet(PO_SUMMARY_SHEET_NAME)
    except gspread.WorksheetNotFound:
        raise ValueError(f"ไม่พบ sheet ชื่อ '{PO_SUMMARY_SHEET_NAME}' ในสเปรดชีต")

    all_values = ws.get_all_values()
    if not all_values:
        raise ValueError(f"Sheet '{PO_SUMMARY_SHEET_NAME}' ว่างเปล่า")

    headers = all_values[0]
    data_rows = all_values[1:]
    col_idx = {name.strip(): i for i, name in enumerate(headers)}

    required_cols = ["Store Name", "Total Items", "Total Amount", "File Name"]
    missing = [c for c in required_cols if c not in col_idx]
    if missing:
        raise ValueError(f"ไม่พบคอลัมน์ {missing} ใน header ของ '{PO_SUMMARY_SHEET_NAME}'")

    matched, unmatched, ambiguous = [], [], []
    used_rows = set()
    updates = []

    for i, path in enumerate(invoice_files, 1):
        filename = os.path.basename(path)
        _status(f"🔎 กำลังตรวจสอบ ({i}/{len(invoice_files)}): {filename}")

        try:
            info = _extract_invoice_info(path)
        except Exception as exc:
            unmatched.append({"file": filename, "reason": f"อ่าน PDF ไม่สำเร็จ: {exc}"})
            continue

        if not info["inv_no"]:
            unmatched.append({"file": filename, "reason": "ไม่พบเลข INV ในไฟล์"})
            continue

        target_amount = info.get(INVOICE_AMOUNT_FIELD)
        if target_amount is None:
            unmatched.append({"file": filename, "reason": "ไม่พบยอดเงินรวมในไฟล์"})
            continue

        candidates = []
        for row_i, row in enumerate(data_rows):
            if row_i in used_rows:
                continue
            try:
                row_amount = float(str(row[col_idx["Total Amount"]]).replace(",", "").strip())
                row_items = int(float(str(row[col_idx["Total Items"]]).replace(",", "").strip()))
            except (ValueError, IndexError):
                continue
            if row_items != info["qty_total"]:
                continue
            if abs(row_amount - target_amount) > AMOUNT_MATCH_TOLERANCE:
                continue
            candidates.append(row_i)

        chosen = None
        if len(candidates) == 1:
            chosen = candidates[0]
        elif len(candidates) > 1 and info["store_hint"]:
            narrowed = [
                r for r in candidates
                if str(data_rows[r][col_idx["Store Name"]]).strip() == info["store_hint"]
            ]
            if len(narrowed) == 1:
                chosen = narrowed[0]

        if chosen is None:
            if not candidates:
                unmatched.append({
                    "file": filename,
                    "reason": f"ไม่พบแถวที่ตรงกัน (จำนวน={info['qty_total']}, ยอด={target_amount:,.2f})"
                })
            else:
                ambiguous.append({
                    "file": filename,
                    "inv_no": info["inv_no"],
                    "candidate_rows": [r + 2 for r in candidates],  # เลขแถวจริงในชีต (1-indexed + header)
                })
            continue

        used_rows.add(chosen)
        sheet_row_number = chosen + 2  # +1 เพราะ header, +1 เพราะ gspread นับแถวเริ่มที่ 1
        from gspread.utils import rowcol_to_a1
        cell = rowcol_to_a1(sheet_row_number, col_idx["File Name"] + 1)
        old_filename = data_rows[chosen][col_idx["File Name"]]
        updates.append({"range": cell, "values": [[info["inv_no"]]]})
        matched.append({
            "file": filename,
            "inv_no": info["inv_no"],
            "sheet_row": sheet_row_number,
            "old_file_name": old_filename,
            "store": data_rows[chosen][col_idx["Store Name"]],
        })

    if updates:
        _status(f"📝 กำลังอัพเดทคอลัมน์ File Name จำนวน {len(updates)} แถว...")
        ws.batch_update(updates, value_input_option="USER_ENTERED")

    _status(
        f"✅ เสร็จสิ้น: match {len(matched)} ไฟล์, "
        f"ไม่พบคู่ {len(unmatched)} ไฟล์, ไม่แน่ใจ {len(ambiguous)} ไฟล์"
    )
    return matched, unmatched, ambiguous


# -----------------------------------------------------------------------
# Google Sheets upload
# -----------------------------------------------------------------------
def update_po_sheet(spreadsheet, final_df: pd.DataFrame, status_cb=None):
    """กรอก Qty2 ลงใน PO sheet (Sheet2) โดย match Store Code กับ header คอลัมน์
    และ Barcode (คอลัมน์สุดท้าย) กับแถว"""
    def _status(msg):
        logger.info(msg)
        if status_cb:
            status_cb(msg)

    _status("📝 กำลังอัพเดท PO sheet...")
    try:
        ws_po = spreadsheet.worksheet("Sheet2")
    except gspread.WorksheetNotFound:
        _status("⚠️ ไม่พบ Sheet2 ข้ามการอัพเดท PO")
        return {}

    all_values = ws_po.get_all_values()
    if not all_values:
        _status("⚠️ Sheet2 ว่างเปล่า")
        return {}

    # หา header row — แถวที่มีชื่อสาขา (col B ขึ้นไปไม่ว่าง)
    header_row_idx = None
    for i, row in enumerate(all_values):
        if any(cell.strip() for cell in row[1:]):
            header_row_idx = i
            break

    if header_row_idx is None:
        _status("⚠️ ไม่พบ header row ใน Sheet2")
        return {}

    headers = all_values[header_row_idx]

    # lookup: Store Code → col index (0-based) ผ่าน STORE_CODE_MAP
    store_col_map = {}
    for col_idx, cell in enumerate(headers):
        cell_stripped = cell.strip()
        if cell_stripped:
            store_col_map[cell_stripped] = col_idx

    # แปลง Store Code → col index โดยใช้ STORE_CODE_MAP
    mapped_store_col = {}
    for code, name in STORE_CODE_MAP.items():
        if name in store_col_map:
            mapped_store_col[code] = store_col_map[name]

    # หา col index ของ "Barcode" จาก header
    barcode_col_idx = None
    for col_idx, cell in enumerate(headers):
        if cell.strip().lower() == "barcode":
            barcode_col_idx = col_idx
            break

    if barcode_col_idx is None:
        _status("⚠️ ไม่พบคอลัมน์ 'Barcode' ใน header ของ Sheet2")
        return {}

    # lookup: Barcode → row index (0-based)
    barcode_row_map = {}
    for row_idx, row in enumerate(all_values):
        if row_idx <= header_row_idx:
            continue
        if len(row) > barcode_col_idx:
            barcode = row[barcode_col_idx].strip()
            if barcode:
                barcode_row_map[barcode] = row_idx

    # รวม Qty2 ของ Store Code + Barcode เดียวกันจากทุก PO ก่อนเขียนลง Sheet2
    # (ถ้าสาขาเดียวกันมีหลาย PO ที่สั่ง Barcode เดิม ต้องบวกกัน ไม่ใช่เขียนทับ)
    qty2_summed = (final_df.groupby(['Store Code', 'Barcode'], as_index=False)['Qty2']
                            .sum())

    # lookup: Store Code → Store Name จริงที่ parse ได้จาก PDF (ใช้แจ้งชื่อสาขาตอน error)
    store_name_lookup = (final_df.assign(**{'Store Code': final_df['Store Code'].astype(str).str.strip()})
                                  .drop_duplicates('Store Code')
                                  .set_index('Store Code')['Store Name']
                                  .to_dict())

    # batch update
    from gspread.utils import rowcol_to_a1
    updates = []
    not_found_stores   = set()
    not_found_barcodes = {}   # barcode -> set ของชื่อสาขาที่หา barcode นี้ใน Sheet2 ไม่เจอ

    for _, row in qty2_summed.iterrows():
        store_code = str(row['Store Code']).strip()
        barcode    = str(row['Barcode']).strip()
        qty2       = row['Qty2']
        store_name = store_name_lookup.get(store_code, store_code)

        col_idx = mapped_store_col.get(store_code)
        row_idx = barcode_row_map.get(barcode)

        if col_idx is None:
            not_found_stores.add(store_code)
            continue
        if row_idx is None:
            not_found_barcodes.setdefault(barcode, set()).add(store_name)
            continue

        cell = rowcol_to_a1(row_idx + 1, col_idx + 1)
        val  = int(qty2) if hasattr(qty2, 'item') else qty2
        updates.append({'range': cell, 'values': [[val]]})

    if not_found_stores:
        logger.warning("ไม่พบ Store Code ใน PO header: %s", not_found_stores)
    if not_found_barcodes:
        logger.warning("ไม่พบ Barcode ใน PO sheet: %s", not_found_barcodes)

    if updates:
        ws_po.batch_update(updates, value_input_option="USER_ENTERED")
        _status(f"✅ อัพเดท PO sheet แล้ว {len(updates)} ช่อง")

        # ไฮไลท์ช่องที่ต่ำกว่าขั้นต่ำ (เทียบกับยอดรวมทุก PO ของสาขานั้น ไม่ใช่ต่อ PO)
        _status("🎨 กำลังไฮไลท์ช่องที่ต่ำกว่าขั้นต่ำ...")
        highlight_cells = []
        clear_cells     = []
        for _, row in qty2_summed.iterrows():
            store_code = str(row['Store Code']).strip()
            barcode    = str(row['Barcode']).strip()
            qty2       = int(row['Qty2']) if hasattr(row['Qty2'], 'item') else row['Qty2']
            minimum    = MIN_ORDER_MAP.get(barcode, 0)

            col_idx = mapped_store_col.get(store_code)
            row_idx = barcode_row_map.get(barcode)
            if col_idx is None or row_idx is None:
                continue

            cell = rowcol_to_a1(row_idx + 1, col_idx + 1)
            if minimum > 0 and qty2 < minimum:
                highlight_cells.append(cell)
            else:
                clear_cells.append(cell)

        if highlight_cells:
            ws_po.format(highlight_cells, {
                "backgroundColor": {"red": 1.0, "green": 0.6, "blue": 0.6}
            })
        if clear_cells:
            ws_po.format(clear_cells, {
                "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}
            })
        _status(f"🔴 ไฮไลท์ {len(highlight_cells)} ช่อง ที่ต่ำกว่าขั้นต่ำ")
    else:
        _status("⚠️ ไม่มีข้อมูลที่ match กับ PO sheet")

    return not_found_barcodes


def _build_min_adjusted_df(df_sorted: pd.DataFrame) -> pd.DataFrame:
    """
    สร้างข้อมูลสำหรับ Sheet10:
    - โครงสร้างเหมือน Sheet1 (ไม่รวม PO)
    - ปรับ Qty2 ให้ไม่ต่ำกว่า MIN_ORDER_MAP
    - Description ทุกแถวดึงจาก BARCODE_DESC (JSON)
    """

    qty2_idx = COLUMNS.index("Qty2")
    amount_idx = COLUMNS.index("Amount")
    total_idx = COLUMNS.index("Total Amount")
    desc_idx = COLUMNS.index("Description")
    barcode_idx = COLUMNS.index("Barcode")

    # รวม Qty2 ต่อ Store Code + Barcode
    qty2_summed = (
        df_sorted.groupby(["Store Code", "Barcode"], as_index=False)["Qty2"]
        .sum()
    )

    summed_map = {
        (str(r["Store Code"]).strip(), str(r["Barcode"]).strip()): int(r["Qty2"])
        for _, r in qty2_summed.iterrows()
    }

    all_rows = []

    # แนะนำให้ group ด้วย Store Code เพื่อไม่ให้ Store Name ซ้ำกันแล้วรวมผิด
    for (store_code, store), grp in df_sorted.groupby(
        ["Store Code", "Store Name"], sort=True
    ):

        for barcode in PREDEFINED_ORDER:

            minimum = MIN_ORDER_MAP.get(barcode, 0)

            total_qty2 = summed_map.get(
                (str(store_code).strip(), str(barcode).strip()),
                0
            )

            shortfall = (
                minimum - total_qty2
                if minimum > 0 and total_qty2 < minimum
                else 0
            )

            matches = grp[grp["Barcode"] == barcode]

            if not matches.empty:

                rows = [r.tolist() for _, r in matches.iterrows()]

                # อัปเดต Description จาก JSON
                for row in rows:
                    bc = str(row[barcode_idx]).strip()
                    row[desc_idx] = BARCODE_DESC.get(bc, row[desc_idx])

                # เพิ่ม Qty2 ให้แถวสุดท้าย
                if shortfall > 0:
                    last = rows[-1]
                    new_qty2 = last[qty2_idx] + shortfall
                    last[qty2_idx] = new_qty2
                    last[total_idx] = int(new_qty2 * last[amount_idx])

                all_rows.extend(rows)

            else:
                # ไม่มี PO ของ Barcode นี้ -> สร้าง Placeholder
                description = BARCODE_DESC.get(str(barcode), "")

                all_rows.append([
                    store_code,          # Store Code
                    store,               # Store Name
                    "",                  # Order No.
                    barcode,             # Barcode
                    description,         # Description จาก JSON
                    "",                  # UOM
                    0,                   # Qty
                    shortfall,           # Qty2
                    0,                   # Amount
                    0                    # Total Amount
                ])

    return pd.DataFrame(all_rows, columns=COLUMNS)

def get_gsheet_client():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)

def upload_to_gsheets(final_df: pd.DataFrame,
                      total_by_store: pd.DataFrame,
                      total_amount_all: float,
                      status_cb=None):
    """
    อัพโหลดข้อมูลลง Google Sheet
    - Sheet tab แรก (WORKSHEET_NAME): ข้อมูลทั้งหมด เรียงตาม Store + Barcode
    - Sheet tab 'Summary': ยอดรวมตาม Store + grand total
    """
    def _status(msg):
        logger.info(msg)
        if status_cb:
            status_cb(msg)

    _status("🔐 กำลังเชื่อมต่อ Google Sheets...")
    client = get_gsheet_client()
    spreadsheet = client.open(SPREADSHEET_NAME)

    # ---- Main data sheet ----
    _status("📋 กำลังเตรียมข้อมูลหลัก...")
    df_sorted = final_df.copy()
    df_sorted['_rank'] = df_sorted['Barcode'].map(lambda b: BARCODE_RANK.get(b, 999))
    df_sorted = (df_sorted.sort_values(['Store Name', '_rank'])
                           .drop(columns='_rank')
                           .reset_index(drop=True))

    # เพิ่มแถว barcode ที่ขาดหายในแต่ละ Store
    # หมายเหตุ: ถ้าสาขาเดียวกันมีหลาย PO ที่สั่ง Barcode เดิม จะแสดง "ทุกแถว" แยกกัน
    # (ไม่ dedup เหลือแถวเดียวเหมือนเดิม) โดยแยกด้วยคอลัมน์ Order No.
    all_rows = []
    for store, grp in df_sorted.groupby('Store Name', sort=True):
        store_code = grp['Store Code'].iloc[0] if not grp.empty else ""
        for barcode in PREDEFINED_ORDER:
            matches = grp[grp['Barcode'] == barcode]
            if not matches.empty:
                for _, r in matches.iterrows():
                    all_rows.append(r.tolist())
            else:
                # ไม่มี PO ใดของสาขานี้สั่ง barcode นี้เลย -> แถว placeholder ค่า 0
                all_rows.append([store_code, store, "", barcode, "", "", 0, 0, 0, 0])

    main_df = pd.DataFrame(all_rows, columns=COLUMNS)

    # แปลง int64/float64 → Python native (gspread ไม่รองรับ numpy types)
    def to_native(val):
        if hasattr(val, 'item'):
            return val.item()
        return val

    main_rows = [[to_native(v) for v in row] for row in main_df.values.tolist()]

    try:
        ws_main = spreadsheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws_main = spreadsheet.add_worksheet(title=WORKSHEET_NAME, rows=5000, cols=20)

    _status(f"⬆️  กำลังอัพโหลดข้อมูลลง '{WORKSHEET_NAME}'...")
    ws_main.clear()
    ws_main.update(
        [COLUMNS] + main_rows,
        value_input_option="USER_ENTERED"
    )

    # จัด format header ให้เป็น bold (A-J เพราะเพิ่มคอลัมน์ Order No. เข้ามา)
    ws_main.format("A1:J1", {"textFormat": {"bold": True}})

    # ---- Sheet10 (เหมือน Sheet1 แต่ปรับยอดให้ไม่ต่ำกว่าขั้นต่ำ) ----
    _status(f"📋 กำลังเตรียมข้อมูล '{SHEET10_NAME}' (ปรับยอดตามขั้นต่ำ)...")
    adjusted_df = _build_min_adjusted_df(df_sorted)
    adjusted_rows = [[to_native(v) for v in row] for row in adjusted_df.values.tolist()]

    try:
        ws_adj = spreadsheet.worksheet(SHEET10_NAME)
    except gspread.WorksheetNotFound:
        ws_adj = spreadsheet.add_worksheet(title=SHEET10_NAME, rows=5000, cols=20)

    _status(f"⬆️  กำลังอัพโหลดข้อมูลลง '{SHEET10_NAME}'...")
    ws_adj.clear()
    ws_adj.update(
        [COLUMNS] + adjusted_rows,
        value_input_option="USER_ENTERED"
    )
    ws_adj.format("A1:J1", {"textFormat": {"bold": True}})

    # ---- Summary sheet ----
    _status("📊 กำลังเขียน Summary sheet...")
    try:
        ws_sum = spreadsheet.worksheet("Summary")
    except gspread.WorksheetNotFound:
        ws_sum = spreadsheet.add_worksheet(title="Summary", rows=200, cols=5)

    summary_rows = [[to_native(v) for v in row] for row in total_by_store.values.tolist()]
    summary_rows.append(["TOTAL", to_native(total_amount_all)])

    ws_sum.clear()
    ws_sum.update(
        [["Store Name", "Total Amount"]] + summary_rows,
        value_input_option="USER_ENTERED"
    )
    ws_sum.format("A1:B1", {"textFormat": {"bold": True}})
    # Grand total row: bold + สีพื้นหลัง
    last_row = len(summary_rows) + 1
    ws_sum.format(f"A{last_row}:B{last_row}", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.9, "green": 0.95, "blue": 0.9}
    })

    # ---- PO sheet (Sheet2) ----
    not_found_barcodes = update_po_sheet(spreadsheet, final_df, status_cb=status_cb)

    _status("✅ อัพโหลดสำเร็จ!")
    return not_found_barcodes or {}


# -----------------------------------------------------------------------
# Google Drive upload (ปี > เดือน > สัปดาห์)
# -----------------------------------------------------------------------
def get_drive_service():
    """
    ล็อกอินด้วยบัญชี Gmail ของผู้ใช้เอง (ไม่ใช่ Service Account) เพื่อให้ไฟล์ที่อัพโหลด
    นับพื้นที่จัดเก็บของบัญชีคนจริง แก้ปัญหา storageQuotaExceeded ของ Service Account
    ครั้งแรกจะเปิดเบราว์เซอร์ให้ล็อกอิน/กด Allow ครั้งเดียว หลังจากนั้นจะจำ token ไว้ใช้ต่อ

    หมายเหตุ: เพราะแอปยังอยู่สถานะ Testing บน Google Cloud Console, token จะหมดอายุ
    ทุก 7 วันโดยอัตโนมัติ (ข้อจำกัดของ Google ไม่เกี่ยวกับโค้ด) — ถ้า refresh token
    ใช้ไม่ได้แล้ว (หมดอายุ/ถูก revoke) จะลบไฟล์ token เก่าทิ้งแล้วเปิดหน้าล็อกอินใหม่
    ให้อัตโนมัติ แทนที่จะโยน error ออกมา
    """
    creds = None
    if os.path.exists(OAUTH_TOKEN_FILE):
        try:
            creds = UserCredentials.from_authorized_user_file(OAUTH_TOKEN_FILE, DRIVE_SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleAuthRequest())
            except Exception as exc:
                # token หมดอายุ/ถูก revoke (เช่น invalid_grant) -> ลบทิ้งแล้วล็อกอินใหม่
                logger.warning("Drive token refresh ไม่สำเร็จ (%s) — จะขอให้ล็อกอินใหม่", exc)
                creds = None
                if os.path.exists(OAUTH_TOKEN_FILE):
                    os.remove(OAUTH_TOKEN_FILE)

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                OAUTH_CLIENT_SECRET_FILE, DRIVE_SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(OAUTH_TOKEN_FILE, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def _get_or_create_drive_folder(service, name: str, parent_id: str) -> str:
    """หาโฟลเดอร์ชื่อ `name` ใต้ parent_id ถ้าไม่มีให้สร้างใหม่ คืนค่า folder id"""
    safe_name = name.replace("'", "\\'")
    query = (
        f"name = '{safe_name}' and '{parent_id}' in parents "
        "and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    resp = service.files().list(
        q=query, spaces="drive", fields="files(id, name)",
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute()
    files = resp.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(
        body=metadata, fields="id", supportsAllDrives=True
    ).execute()
    return folder["id"]


def upload_pdfs_to_drive(pdf_folder: str, status_cb=None):
    """
    อัพโหลดไฟล์ PDF ทั้งหมดในโฟลเดอร์ pdf_folder ขึ้น Google Drive
    โดยสร้าง/ใช้โครงสร้างโฟลเดอร์ ปี(พ.ศ.) > เดือน > สัปดาห์ที่ N
    (อิงจากวันที่ปัจจุบันตอนกดอัพโหลด) ใต้ DRIVE_PARENT_FOLDER_ID
    ไฟล์ชื่อซ้ำในโฟลเดอร์ปลายทางจะถูกข้าม ไม่อัพโหลดซ้ำ
    """
    def _status(msg):
        logger.info(msg)
        if status_cb:
            status_cb(msg)

    pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"ไม่พบไฟล์ PDF ในโฟลเดอร์: {pdf_folder}")

    today = date.today()
    year_name  = str(today.year + 543)              # ปี พ.ศ.
    month_name = THAI_MONTHS[today.month - 1]        # ชื่อเดือนภาษาไทย
    week_no    = (today.day - 1) // 7 + 1            # สัปดาห์ที่เท่าไหร่ของเดือน
    week_name  = f"สัปดาห์ที่ {week_no}"

    _status("🔐 กำลังเชื่อมต่อ Google Drive...")
    service = get_drive_service()

    _status(f"📁 กำลังสร้าง/ค้นหาโฟลเดอร์ {year_name} > {month_name} > {week_name} ...")
    year_id  = _get_or_create_drive_folder(service, year_name, DRIVE_PARENT_FOLDER_ID)
    month_id = _get_or_create_drive_folder(service, month_name, year_id)
    week_id  = _get_or_create_drive_folder(service, week_name, month_id)

    uploaded, skipped = 0, 0
    for i, path in enumerate(pdf_files, 1):
        filename = os.path.basename(path)
        _status(f"⬆️  กำลังอัพโหลด ({i}/{len(pdf_files)}): {filename}")

        # กันอัพโหลดซ้ำ: ถ้ามีไฟล์ชื่อเดียวกันในโฟลเดอร์สัปดาห์นี้อยู่แล้ว ให้ข้าม
        safe_name = filename.replace("'", "\\'")
        query = f"name = '{safe_name}' and '{week_id}' in parents and trashed = false"
        resp = service.files().list(
            q=query, spaces="drive", fields="files(id)", supportsAllDrives=True
        ).execute()
        if resp.get("files"):
            skipped += 1
            continue

        media = MediaFileUpload(path, mimetype="application/pdf", resumable=True)
        service.files().create(
            body={"name": filename, "parents": [week_id]},
            media_body=media, fields="id", supportsAllDrives=True,
        ).execute()
        uploaded += 1

    _status(f"✅ อัพโหลดขึ้น Google Drive เสร็จสิ้น: {uploaded} ไฟล์ (ข้ามไฟล์ซ้ำ {skipped} ไฟล์)")
    return uploaded, skipped, f"{year_name}/{month_name}/{week_name}"


# -----------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------
_last_pdf_folder = None  # โฟลเดอร์ PDF ล่าสุดที่ประมวลผลสำเร็จ (ใช้โดยปุ่ม Upload to Drive)


def show_summary(total_by_store: pd.DataFrame, total_amount_all: float):
    win = tk.Toplevel(root)
    win.title("ยอดรวมตามสาขา")
    win.resizable(False, False)

    ttk.Label(win, text="ยอดรวม Total Amount ตามสาขา",
              font=("", 12, "bold")).pack(pady=(14, 6), padx=20)

    frame = ttk.Frame(win)
    frame.pack(padx=20, pady=(0, 6))

    cols = ["Store Name", "Total Amount"]
    tree = ttk.Treeview(frame, columns=cols, show="headings", height=min(len(total_by_store), 15))
    tree.heading("Store Name",   text="Store Name")
    tree.heading("Total Amount", text="Total Amount")
    tree.column("Store Name",   width=220, anchor="w")
    tree.column("Total Amount", width=140, anchor="e")

    for row in total_by_store.itertuples(index=False):
        tree.insert('', tk.END, values=[row[0], f"{row[1]:,.0f}"])

    # Grand total row (tag สีต่าง)
    tree.insert('', tk.END, values=["TOTAL", f"{total_amount_all:,.0f}"], tags=("total",))
    tree.tag_configure("total", background="#d4edda", font=("", 10, "bold"))

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0)
    vsb.grid(row=0, column=1, sticky="ns")

    ttk.Button(win, text="ปิด", command=win.destroy, padding=(20, 6)).pack(pady=(6, 14))


def upload_to_drive_clicked():
    """Handler ของปุ่ม 'อัพโหลด PDF ไป Google Drive' บนหน้าต่างหลัก"""
    if not _last_pdf_folder:
        messagebox.showwarning("ยังไม่มีข้อมูล", "กรุณาเลือกโฟลเดอร์ PDF และประมวลผลให้เสร็จก่อน")
        return

    prog_win = tk.Toplevel(root)
    prog_win.title("กำลังอัพโหลดขึ้น Google Drive...")
    prog_win.resizable(False, False)
    status_var = tk.StringVar(value="กำลังเริ่มอัพโหลด...")
    ttk.Label(prog_win, textvariable=status_var, wraplength=360).pack(padx=20, pady=20)

    def update_status(msg):
        status_var.set(msg)
        prog_win.update_idletasks()

    drive_btn.config(state="disabled")

    def worker():
        try:
            uploaded, skipped, path_str = upload_pdfs_to_drive(
                _last_pdf_folder,
                status_cb=lambda msg: root.after(0, lambda: update_status(msg))
            )
            root.after(0, lambda: messagebox.showinfo(
                "อัพโหลดสำเร็จ",
                f"อัพโหลดไฟล์ PDF ขึ้น Google Drive แล้ว {uploaded} ไฟล์\n"
                f"(ข้ามไฟล์ซ้ำ {skipped} ไฟล์)\n\n"
                f"ที่โฟลเดอร์: {path_str}"
            ))
        except FileNotFoundError as exc:
            root.after(0, lambda: messagebox.showerror("ไม่พบไฟล์", str(exc)))
        except Exception as exc:
            root.after(0, lambda: messagebox.showerror("Error", str(exc)))
        finally:
            root.after(0, prog_win.destroy)
            root.after(0, lambda: drive_btn.config(state="normal"))

    threading.Thread(target=worker, daemon=True).start()


def show_invoice_match_result(matched, unmatched, ambiguous):
    win = tk.Toplevel(root)
    win.title("ผลการจับคู่ Invoice กับ PO Summary")
    win.resizable(False, False)

    ttk.Label(win, text=f"✅ Match สำเร็จ {len(matched)} ไฟล์ | "
                         f"⚠️ ไม่แน่ใจ {len(ambiguous)} ไฟล์ | "
                         f"❌ ไม่พบคู่ {len(unmatched)} ไฟล์",
              font=("", 11, "bold")).pack(pady=(14, 8), padx=20)

    frame = ttk.Frame(win)
    frame.pack(padx=20, pady=(0, 6))

    cols = ["สถานะ", "ไฟล์", "รายละเอียด"]
    height = min(max(len(matched) + len(unmatched) + len(ambiguous), 1), 18)
    tree = ttk.Treeview(frame, columns=cols, show="headings", height=height)
    tree.heading("สถานะ", text="สถานะ")
    tree.heading("ไฟล์", text="ไฟล์")
    tree.heading("รายละเอียด", text="รายละเอียด")
    tree.column("สถานะ", width=70, anchor="center")
    tree.column("ไฟล์", width=260, anchor="w")
    tree.column("รายละเอียด", width=300, anchor="w")

    for m in matched:
        tree.insert('', tk.END, values=(
            "✅", m["file"],
            f"{m['store']} → File Name เปลี่ยนเป็น {m['inv_no']} (แถว {m['sheet_row']})"
        ), tags=("ok",))
    for a in ambiguous:
        tree.insert('', tk.END, values=(
            "⚠️", a["file"],
            f"INV {a['inv_no']} ตรงได้หลายแถว: {a['candidate_rows']} — ตรวจสอบเอง"
        ), tags=("warn",))
    for u in unmatched:
        tree.insert('', tk.END, values=("❌", u["file"], u["reason"]), tags=("bad",))

    tree.tag_configure("ok", background="#d4edda")
    tree.tag_configure("warn", background="#fff3cd")
    tree.tag_configure("bad", background="#f8d7da")

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0)
    vsb.grid(row=0, column=1, sticky="ns")

    ttk.Button(win, text="ปิด", command=win.destroy, padding=(20, 6)).pack(pady=(10, 14))


def match_invoices_clicked():
    """Handler ของปุ่ม 'จับคู่ Invoice -> อัพเดท PO Summary'"""
    folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ที่เก็บใบ Invoice (มีเลข INV)")
    if not folder:
        return

    prog_win = tk.Toplevel(root)
    prog_win.title("กำลังจับคู่ Invoice...")
    prog_win.resizable(False, False)
    status_var = tk.StringVar(value="กำลังเริ่มตรวจสอบ...")
    ttk.Label(prog_win, textvariable=status_var, wraplength=360).pack(padx=20, pady=20)

    def update_status(msg):
        status_var.set(msg)
        prog_win.update_idletasks()

    match_btn.config(state="disabled")

    def worker():
        try:
            matched, unmatched, ambiguous = match_invoices_to_po_summary(
                folder,
                status_cb=lambda msg: root.after(0, lambda: update_status(msg))
            )
            root.after(0, lambda: show_invoice_match_result(matched, unmatched, ambiguous))
        except FileNotFoundError as exc:
            root.after(0, lambda: messagebox.showerror("ไม่พบไฟล์", str(exc)))
        except ValueError as exc:
            root.after(0, lambda: messagebox.showerror("ไม่พบข้อมูลใน Sheet", str(exc)))
        except gspread.SpreadsheetNotFound:
            root.after(0, lambda: messagebox.showerror(
                "Google Sheet ไม่พบ",
                f"ไม่พบ Spreadsheet ชื่อ '{SPREADSHEET_NAME}'"
            ))
        except Exception as exc:
            root.after(0, lambda: messagebox.showerror("Error", str(exc)))
        finally:
            root.after(0, prog_win.destroy)
            root.after(0, lambda: match_btn.config(state="normal"))

    threading.Thread(target=worker, daemon=True).start()


def select_folder():
    global _last_pdf_folder
    folder = filedialog.askdirectory()
    if not folder:
        return

    # Progress window
    prog_win = tk.Toplevel(root)
    prog_win.title("กำลังประมวลผล...")
    prog_win.resizable(False, False)
    prog_bar = ttk.Progressbar(prog_win, length=340, mode="determinate")
    prog_bar.pack(padx=20, pady=(16, 4))
    status_var = tk.StringVar(value="กำลังอ่านไฟล์ PDF...")
    ttk.Label(prog_win, textvariable=status_var, wraplength=340).pack(padx=20, pady=(0, 16))

    def update_progress(done, total):
        prog_bar['maximum'] = total
        prog_bar['value']   = done
        status_var.set(f"อ่านไฟล์ {done} / {total}")
        prog_win.update_idletasks()

    def update_status(msg):
        status_var.set(msg)
        prog_win.update_idletasks()

    def worker():
        try:
            final_df, total_by_store, total_amount_all = read_multiple_pdfs(
                folder, progress_cb=update_progress
            )
            update_status("กำลังอัพโหลดไปยัง Google Sheets...")
            not_found_barcodes = upload_to_gsheets(
                final_df, total_by_store, total_amount_all,
                status_cb=lambda msg: root.after(0, lambda: update_status(msg))
            )
            if not_found_barcodes:
                lines = []
                for barcode in sorted(not_found_barcodes):
                    stores = ", ".join(sorted(not_found_barcodes[barcode]))
                    lines.append(f"• {barcode}  (สาขา: {stores})")
                barcode_list = "\n".join(lines)
                root.after(0, lambda: messagebox.showwarning(
                    "ไม่พบ Barcode ใน PO Sheet",
                    f"พบ Barcode ต่อไปนี้ในข้อมูล PDF แต่หาไม่เจอใน Sheet2 (PO sheet):\n\n"
                    f"{barcode_list}\n\n"
                    "ตรวจสอบว่า Sheet2 มีแถวของ Barcode เหล่านี้ครบหรือไม่"
                ))

            # บันทึกโฟลเดอร์ PDF ล่าสุด แล้วเปิดใช้งานปุ่ม Upload to Drive
            global _last_pdf_folder
            _last_pdf_folder = folder
            root.after(0, lambda: drive_btn.config(state="normal"))

            root.after(0, lambda: show_summary(total_by_store, total_amount_all))
        except FileNotFoundError as exc:
            root.after(0, lambda: messagebox.showerror("ไม่พบไฟล์", str(exc)))
        except gspread.SpreadsheetNotFound:
            root.after(0, lambda: messagebox.showerror(
                "Google Sheet ไม่พบ",
                f"ไม่พบ Spreadsheet ชื่อ '{SPREADSHEET_NAME}'\n"
                "ตรวจสอบว่าชื่อถูกต้องและได้แชร์ให้ Service Account แล้ว"
            ))
        except Exception as exc:
            root.after(0, lambda: messagebox.showerror("Error", str(exc)))
        finally:
            root.after(0, prog_win.destroy)

    threading.Thread(target=worker, daemon=True).start()


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("PDF → Google Sheets")
    root.configure(bg="#f0f0f0")
    root.geometry("340x280")

    ttk.Label(root, text="📄 PDF → Google Sheets", font=("", 13, "bold"),
              background="#f0f0f0").pack(pady=(20, 6))
    ttk.Label(root, text=f"Sheet: {SPREADSHEET_NAME}",
              background="#f0f0f0", foreground="#666").pack()
    ttk.Button(root, text="📂  เลือกโฟลเดอร์ PDF",
               command=select_folder, padding=(20, 8)).pack(pady=(16, 6))

    drive_btn = ttk.Button(root, text="☁️  อัพโหลด PDF ไป Google Drive",
                            command=upload_to_drive_clicked,
                            state="disabled", padding=(20, 8))
    drive_btn.pack(pady=(0, 10))

    match_btn = ttk.Button(root, text="🔗  จับคู่ Invoice → อัพเดท PO Summary",
                            command=match_invoices_clicked, padding=(20, 8))
    match_btn.pack(pady=(0, 16))

    root.mainloop()
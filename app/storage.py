"""บันทึกข้อมูลที่ลูกค้าส่งเข้ามา: คำสั่งซื้อ · แจ้งชำระเงิน · ข้อความติดต่อ

เก็บเป็นไฟล์ JSON ในโฟลเดอร์ _data/ (อยู่ใน .gitignore)
ไฟล์สลิปเก็บใน _data/slips/ ซึ่งอยู่นอก /static — เปิดดูได้เฉพาะแอดมิน
"""

import json
import secrets
import threading
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "_data"
SLIPS_DIR = DATA_DIR / "slips"

_ORDERS_FILE = DATA_DIR / "orders.json"
_MESSAGES_FILE = DATA_DIR / "messages.json"
_PAYMENTS_FILE = DATA_DIR / "payments.json"

_lock = threading.Lock()

SLIP_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
MAX_SLIP_BYTES = 5 * 1024 * 1024      # 5 MB
_CHUNK = 64 * 1024

# ── สถานะคำสั่งซื้อ ───────────────────────────────────────
# new    = รอชำระเงิน
# review = ลูกค้าแจ้งโอนแล้ว รอแอดมินตรวจสลิป
# paid   = แอดมินยืนยันแล้วว่าเงินเข้าจริง
ORDER_STATUSES = {
    "new":    {"label": "รอชำระเงิน",  "css": "st-new"},
    "review": {"label": "รอตรวจสลิป",  "css": "st-review"},
    "paid":   {"label": "ชำระแล้ว",    "css": "st-paid"},
}

# ── สถานะการแจ้งชำระเงิน ──────────────────────────────────
PAYMENT_STATUSES = {
    "pending":  {"label": "รอตรวจสอบ", "css": "st-review"},
    "approved": {"label": "ยืนยันแล้ว", "css": "st-paid"},
    "rejected": {"label": "ปฏิเสธ",     "css": "st-reject"},
}


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    return data if isinstance(data, list) else []


def _write(path: Path, rows: list[dict]) -> None:
    """เขียนแบบ atomic — เขียนไฟล์ชั่วคราวก่อนแล้วค่อยสลับ กันไฟล์พังกลางคัน"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _append(path: Path, row: dict) -> dict:
    with _lock:
        rows = _read(path)
        rows.append(row)
        _write(path, rows)
    return row


def _patch(path: Path, key: str, value: str, changes: dict) -> dict | None:
    """แก้ไขแถวแรกที่ row[key] == value แล้วบันทึก คืนแถวที่แก้ (None ถ้าไม่พบ)"""
    with _lock:
        rows = _read(path)
        target = next((r for r in rows if r.get(key) == value), None)
        if target is None:
            return None
        target.update(changes)
        _write(path, rows)
    return target


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_order_no() -> str:
    """เลขที่คำสั่งซื้อ เช่น KS-260809-4F1A"""
    return f"KS-{datetime.now():%y%m%d}-{secrets.token_hex(2).upper()}"


# ── คำสั่งซื้อ ────────────────────────────────────────────
def save_order(customer: dict, items: list[dict], total: int) -> dict:
    order = {
        "order_no": new_order_no(),
        "created_at": _now(),
        "status": "new",
        "customer": customer,
        "items": [
            {
                "product_id": i["product_id"],
                "name": i["name"],
                "size": i["size"],
                "qty": i["qty"],
                "price": i["price"],
                "subtotal": i["price"] * i["qty"],
            }
            for i in items
        ],
        "total": total,
    }
    return _append(_ORDERS_FILE, order)


def list_orders() -> list[dict]:
    """คำสั่งซื้อทั้งหมด เรียงใหม่สุดขึ้นก่อน"""
    return sorted(_read(_ORDERS_FILE), key=lambda o: o.get("created_at", ""), reverse=True)


def normalize_order_no(text: str) -> str:
    """ทำความสะอาดเลขที่ลูกค้าพิมพ์มา เช่น ' #ks-260809-9f29 ' -> 'KS-260809-9F29'"""
    return (text or "").strip().lstrip("#").strip().upper()


def get_order(order_no: str) -> dict | None:
    """หาคำสั่งซื้อจากเลขที่ (ไม่สนตัวพิมพ์เล็ก/ใหญ่ และ # นำหน้า)"""
    wanted = normalize_order_no(order_no)
    if not wanted:
        return None
    return next(
        (o for o in _read(_ORDERS_FILE)
         if normalize_order_no(o.get("order_no", "")) == wanted),
        None,
    )


def get_orders(order_nos: list[str]) -> list[dict]:
    """ดึงคำสั่งซื้อหลายรายการตามเลขที่ เรียงใหม่สุดขึ้นก่อน (ข้ามเลขที่ไม่มีจริง)"""
    wanted = {normalize_order_no(n) for n in order_nos}
    rows = [o for o in _read(_ORDERS_FILE)
            if normalize_order_no(o.get("order_no", "")) in wanted]
    return sorted(rows, key=lambda o: o.get("created_at", ""), reverse=True)


def set_order_status(order_no: str, status: str) -> dict | None:
    """เปลี่ยนสถานะคำสั่งซื้อ (รับเฉพาะสถานะที่กำหนดไว้เท่านั้น)"""
    if status not in ORDER_STATUSES:
        return None
    order = get_order(order_no)
    if not order:
        return None
    return _patch(_ORDERS_FILE, "order_no", order["order_no"],
                  {"status": status, "status_at": _now()})


# ── ข้อความติดต่อ ─────────────────────────────────────────
def save_message(name: str, contact: str, topic: str, message: str) -> dict:
    return _append(_MESSAGES_FILE, {
        "id": secrets.token_hex(4),
        "created_at": _now(),
        "name": name,
        "contact": contact,
        "topic": topic,
        "message": message,
    })


def list_messages() -> list[dict]:
    return sorted(_read(_MESSAGES_FILE), key=lambda m: m.get("created_at", ""), reverse=True)


# ── แจ้งชำระเงิน ──────────────────────────────────────────
def save_payment(order_id: str, amount: str, method: str,
                 slip_file: str | None) -> tuple[dict, dict | None]:
    """บันทึกการแจ้งชำระเงิน แล้วผูกเข้ากับคำสั่งซื้อถ้าเลขที่ตรงกับของจริง

    คืน (payment, order) — order เป็น None เมื่อเลขที่ไม่ตรงกับคำสั่งซื้อใด
    คำสั่งซื้อที่ผูกได้จะถูกเปลี่ยนสถานะเป็น "รอตรวจสลิป" อัตโนมัติ
    """
    order = get_order(order_id)
    payment = _append(_PAYMENTS_FILE, {
        "id": secrets.token_hex(4),
        "created_at": _now(),
        "order_id": order_id,                              # ตามที่ลูกค้ากรอกมา
        "order_no": order["order_no"] if order else None,  # เลขที่ยืนยันแล้ว
        "amount": amount,
        "method": method,
        "slip": slip_file,
        "status": "pending",
    })

    if order:
        # ที่ชำระแล้วไม่ต้องถอยกลับไปรอตรวจซ้ำ
        if order.get("status") != "paid":
            set_order_status(order["order_no"], "review")
        order = get_order(order["order_no"])

    return payment, order


def list_payments() -> list[dict]:
    return sorted(_read(_PAYMENTS_FILE), key=lambda p: p.get("created_at", ""), reverse=True)


def get_payment(payment_id: str) -> dict | None:
    return next((p for p in _read(_PAYMENTS_FILE) if p.get("id") == payment_id), None)


def review_payment(payment_id: str, approve: bool) -> dict | None:
    """แอดมินยืนยัน/ปฏิเสธสลิป — อัปเดตสถานะคำสั่งซื้อที่ผูกไว้ตามไปด้วย"""
    payment = get_payment(payment_id)
    if not payment:
        return None

    payment = _patch(_PAYMENTS_FILE, "id", payment_id, {
        "status": "approved" if approve else "rejected",
        "reviewed_at": _now(),
    })

    order_no = payment.get("order_no")
    if order_no:
        # ปฏิเสธแล้วให้กลับไปรอชำระ เว้นแต่มีสลิปใบอื่นที่ยังรอตรวจอยู่
        if approve:
            set_order_status(order_no, "paid")
        elif any(p.get("order_no") == order_no and p.get("status") == "pending"
                 for p in _read(_PAYMENTS_FILE)):
            set_order_status(order_no, "review")
        else:
            set_order_status(order_no, "new")
    return payment


async def write_upload(upload: UploadFile, dest: Path, max_bytes: int) -> str | None:
    """เขียนไฟล์อัปโหลดลง dest แบบทีละก้อน จำกัดขนาดไม่ให้เกิน max_bytes

    คืน None ถ้าสำเร็จ หรือรหัสข้อผิดพลาด ("size" / "write")
    ถ้าไฟล์ใหญ่เกินกำหนดจะลบไฟล์ที่เขียนค้างไว้ทิ้งทันที
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    try:
        with dest.open("wb") as fh:
            while chunk := await upload.read(_CHUNK):
                written += len(chunk)
                if written > max_bytes:
                    fh.close()
                    dest.unlink(missing_ok=True)
                    return "size"
                fh.write(chunk)
    except OSError:
        dest.unlink(missing_ok=True)
        return "write"
    return None


async def save_slip(upload: UploadFile | None) -> tuple[str | None, str | None]:
    """บันทึกไฟล์สลิป คืน (ชื่อไฟล์, รหัสข้อผิดพลาด)"""
    if upload is None or not upload.filename:
        return None, None

    ext = Path(upload.filename).suffix.lower()
    if ext not in SLIP_ALLOWED_EXT:
        return None, "type"

    filename = f"slip_{datetime.now():%y%m%d_%H%M%S}_{secrets.token_hex(3)}{ext}"
    err = await write_upload(upload, SLIPS_DIR / filename, MAX_SLIP_BYTES)
    return (None, err) if err else (filename, None)


def slip_path(filename: str) -> Path | None:
    """หาไฟล์สลิปจากชื่อ — กัน path traversal โดยรับเฉพาะชื่อไฟล์ล้วน"""
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return None
    path = SLIPS_DIR / filename
    return path if path.is_file() else None

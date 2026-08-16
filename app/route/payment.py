from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse

import notify
import storage
from core import templates
from data import get_cart_count

from .order import my_order_numbers

router = APIRouter(prefix="/payment")


# ── พร้อมเพย์ (ของจริง) ───────────────────────────────────
# ใช้รูป QR จริงที่บันทึกไว้ที่ static/images/ แทนการสร้าง QR เอง
# เพราะเป็น QR ผูกบัญชีธนาคาร ไม่ใช่ QR แบบผูกเบอร์
PROMPTPAY_NAME = "ด.ช. คุณากร ผาสุข"
PROMPTPAY_ACCOUNT = "xxx-x-x4937-x"          # เลขบัญชีที่ธนาคารปิดบางส่วนไว้
PROMPTPAY_QR_IMAGE = "promptpay.jpg"

# ── ข้อมูลบัญชีจำลอง (เดโม) ─────────────────────────────

BANK_ACCOUNTS = [
    {
        "bank": "ธนาคารกสิกรไทย",
        "short": "KBANK",
        "color": "#138f2d",
        "number": "123-4-56789-0",
        "name": "บจก. คุณากร สปอร์ต",
        "branch": "สาขาสุขุมวิท",
        "type": "ออมทรัพย์",
    },
    {
        "bank": "ธนาคารไทยพาณิชย์",
        "short": "SCB",
        "color": "#4e2a84",
        "number": "987-6-54321-0",
        "name": "บจก. คุณากร สปอร์ต",
        "branch": "สาขาคลองเตย",
        "type": "ออมทรัพย์",
    },
    {
        "bank": "ธนาคารกรุงเทพ",
        "short": "BBL",
        "color": "#1e4598",
        "number": "111-2-33445-6",
        "name": "บจก. คุณากร สปอร์ต",
        "branch": "สาขาพระราม 4",
        "type": "กระแสรายวัน",
    },
]


def _crc16(payload: str) -> str:
    """CRC-16/CCITT-FALSE ตามสเปก EMVCo ของ PromptPay"""
    crc = 0xFFFF
    for ch in payload.encode("ascii"):
        crc ^= ch << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def _tlv(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"


def build_promptpay_payload(mobile: str, amount: float | None = None) -> str:
    """สร้าง payload มาตรฐาน EMVCo สำหรับ PromptPay (สแกนได้จริง)"""
    digits = "".join(c for c in mobile if c.isdigit())
    acc = "0066" + digits[1:] if digits.startswith("0") else "0066" + digits
    merchant = _tlv("00", "A000000677010111") + _tlv("01", acc)
    payload = (
        _tlv("00", "01")
        + _tlv("01", "12" if amount else "11")
        + _tlv("29", merchant)
        + _tlv("53", "764")
        + _tlv("58", "TH")
    )
    if amount:
        payload += _tlv("54", f"{amount:.2f}")
    payload += "6304"
    return payload + _crc16(payload)


@router.get("/", response_class=HTMLResponse)
async def payment(request: Request, done: int = 0, error: str = None,
                  unmatched: str = None):
    # คำสั่งซื้อของลูกค้าคนนี้ที่ยังไม่ได้ยืนยันการชำระ -> ให้เลือกจากรายการแทนการพิมพ์
    my_orders = [o for o in storage.get_orders(my_order_numbers(request))
                 if o.get("status") != "paid"]
    return templates.TemplateResponse(request, "payment.html", {
        "cart_count": get_cart_count(request),
        "accounts": BANK_ACCOUNTS,
        "promptpay_name": PROMPTPAY_NAME,
        "promptpay_account": PROMPTPAY_ACCOUNT,
        "promptpay_qr_image": PROMPTPAY_QR_IMAGE,
        "done": bool(done),
        "error": error,
        "unmatched": unmatched,
        "my_orders": my_orders,
    })


@router.post("/notify")
async def payment_notify(
    order_id: str = Form(""),
    order_id_manual: str = Form(""),
    amount: str = Form(""),
    method: str = Form("โอนธนาคาร"),
    slip: UploadFile = File(None),
):
    # เลขที่พิมพ์เองมาก่อนเสมอ (ใช้เมื่อสั่งจากเครื่องอื่นหรือช่องทางอื่น)
    entered = storage.normalize_order_no(order_id_manual or order_id)

    slip_file, err = await storage.save_slip(slip)
    if err:
        return RedirectResponse(url=f"/payment/?error={err}#notify", status_code=303)

    payment, order = storage.save_payment(
        order_id=entered,
        amount=amount.strip(),
        method=method.strip() or "โอนธนาคาร",
        slip_file=slip_file,
    )
    notify.new_payment(payment, order)

    # เลขที่ไม่ตรงกับคำสั่งซื้อใด -> รับเรื่องไว้ แต่บอกลูกค้าว่าจะตรวจสอบให้เอง
    if entered and not order:
        return RedirectResponse(
            url=f"/payment/?done=1&unmatched={entered}#notify", status_code=303
        )
    return RedirectResponse(url="/payment/?done=1#notify", status_code=303)

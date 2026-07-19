from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse

from core import templates
from data import get_cart_count

router = APIRouter(prefix="/payment")


# ── ข้อมูลบัญชีจำลอง (เดโม) ─────────────────────────────
PROMPTPAY_ID = "0812345678"          # เบอร์พร้อมเพย์ (จำลอง)
PROMPTPAY_NAME = "บจก. คุณากร สปอร์ต"

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
async def payment(request: Request, done: int = 0):
    return templates.TemplateResponse(request, "payment.html", {
        "cart_count": get_cart_count(),
        "accounts": BANK_ACCOUNTS,
        "promptpay_id": PROMPTPAY_ID,
        "promptpay_name": PROMPTPAY_NAME,
        "promptpay_payload": build_promptpay_payload(PROMPTPAY_ID),
        "done": bool(done),
    })


@router.post("/notify")
async def payment_notify(
    order_id: str = Form(""),
    amount: str = Form(""),
    method: str = Form("โอนธนาคาร"),
    slip: UploadFile = File(None),
):
    # เดโม: รับแจ้งชำระเงินแล้วส่งกลับหน้าเดิมพร้อมสถานะสำเร็จ
    return RedirectResponse(url="/payment/?done=1#notify", status_code=303)

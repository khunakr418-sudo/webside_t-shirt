import re
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

import notify
import storage
from core import templates
from data import (
    PRODUCTS, IMAGES_DIR, MAX_IMAGES, IMAGE_SLOTS,
    get_cart_count, set_product_image, remove_product_image, update_product,
)
from security import (
    check_credentials, is_admin, lockout_remaining, login_admin, logout_admin,
    record_failure, require_admin, reset_failures, safe_next,
)

router = APIRouter(prefix="/admin")
# ทุกเส้นทางในนี้ต้องล็อกอินก่อน (หน้า login/logout อยู่นอกกลุ่มนี้)
protected = APIRouter(dependencies=[Depends(require_admin)])

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _hex_or(value: str, fallback: str) -> str:
    """ตรวจสอบรหัสสี #rrggbb ถ้าไม่ถูกต้องใช้ค่าเดิม"""
    value = (value or "").strip()
    return value if _HEX_RE.match(value) else fallback


# ── เข้าสู่ระบบ / ออกจากระบบ ──────────────────────────────
@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, next: str = "/admin/", error: str = None):
    if is_admin(request):
        return RedirectResponse(url=safe_next(next), status_code=303)
    return templates.TemplateResponse(request, "admin_login.html", {
        "cart_count": get_cart_count(request),
        "next": safe_next(next),
        "error": error,
        "locked": lockout_remaining(request),
    })


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/admin/"),
):
    target = safe_next(next)

    if lockout_remaining(request):
        return RedirectResponse(
            url=f"/admin/login?next={target}&error=locked", status_code=303
        )

    if not check_credentials(username, password):
        record_failure(request)
        return RedirectResponse(
            url=f"/admin/login?next={target}&error=bad", status_code=303
        )

    reset_failures(request)
    login_admin(request)
    return RedirectResponse(url=target, status_code=303)


@router.get("/logout")
async def logout(request: Request):
    logout_admin(request)
    return RedirectResponse(url="/admin/login", status_code=303)


# ── จัดการสินค้า ──────────────────────────────────────────
@protected.get("/", response_class=HTMLResponse)
async def admin(request: Request, ok: int = None, error: str = None):
    return templates.TemplateResponse(request, "admin.html", {
        "products": PRODUCTS,
        "slots": IMAGE_SLOTS,
        "cart_count": get_cart_count(request),
        "ok": ok,
        "error": error,
    })


@protected.post("/upload")
async def upload_image(
    product_id: int = Form(...),
    slot: int = Form(...),
    image: UploadFile = File(...),
):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    if slot < 0 or slot >= MAX_IMAGES:
        return RedirectResponse(url="/admin/?error=slot", status_code=303)

    ext = Path(image.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        return RedirectResponse(url="/admin/?error=type", status_code=303)

    # ชื่อไฟล์ใหม่ระบุช่อง + timestamp -> เบราว์เซอร์โหลดรูปใหม่ทันที
    filename = f"product_{product_id}_s{slot}_{int(time.time())}{ext}"
    err = await storage.write_upload(image, IMAGES_DIR / filename, MAX_IMAGE_BYTES)
    if err:
        return RedirectResponse(url=f"/admin/?error={err}", status_code=303)

    # ลบไฟล์เดิมในช่องนี้หลังบันทึกไฟล์ใหม่สำเร็จ เพื่อไม่ให้ไฟล์ค้าง
    old = product["images"][slot] if slot < len(product["images"]) else None
    if old and old != filename:
        (IMAGES_DIR / old).unlink(missing_ok=True)

    set_product_image(product_id, slot, filename)
    return RedirectResponse(url=f"/admin/?ok={product_id}", status_code=303)


@protected.post("/update")
async def update_product_details(
    product_id: int = Form(...),
    name: str = Form(...),
    brand: str = Form(""),
    subtitle: str = Form(""),
    type: str = Form("short"),
    badge: str = Form(""),
    price: int = Form(...),
    old_price: int = Form(0),
    bulk10: int = Form(0),
    bulk50: int = Form(0),
    rating: float = Form(5.0),
    reviews_count: int = Form(0),
    sold: int = Form(0),
    stock: int = Form(0),
    material: str = Form(""),
    care: str = Form(""),
    features: str = Form(""),
    c1: str = Form("#009688"),
    c2: str = Form("#00796b"),
    c3: str = Form("#e0f2f1"),
):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")

    fields = {
        "name": name.strip() or product["name"],
        "brand": brand.strip(),
        "subtitle": subtitle.strip(),
        "type": type if type in ("short", "long") else product["type"],
        "badge": badge.strip(),
        "price": max(0, price),
        "old_price": max(0, old_price),
        "bulk10": max(0, bulk10),
        "bulk50": max(0, bulk50),
        "rating": min(5.0, max(0.0, round(rating, 1))),
        "reviews_count": max(0, reviews_count),
        "sold": max(0, sold),
        "stock": max(0, stock),
        "material": material.strip(),
        "care": care.strip(),
        # จุดเด่น: บรรทัดละ 1 ข้อ ตัดบรรทัดว่างทิ้ง
        "features": [ln.strip() for ln in features.splitlines() if ln.strip()],
        "c1": _hex_or(c1, product["c1"]),
        "c2": _hex_or(c2, product["c2"]),
        "c3": _hex_or(c3, product["c3"]),
    }
    update_product(product_id, fields)
    return RedirectResponse(url=f"/admin/?ok={product_id}", status_code=303)


@protected.post("/remove")
async def remove_image(product_id: int = Form(...), slot: int = Form(...)):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")

    old = product["images"][slot] if 0 <= slot < len(product["images"]) else None
    if old:
        (IMAGES_DIR / old).unlink(missing_ok=True)

    remove_product_image(product_id, slot)
    return RedirectResponse(url=f"/admin/?ok={product_id}", status_code=303)


# ── คำสั่งซื้อ · แจ้งชำระเงิน · ข้อความติดต่อ ──────────────
@protected.get("/orders", response_class=HTMLResponse)
async def admin_orders(request: Request, tab: str = "orders",
                       ntok: str = None, nterr: str = None):
    if tab not in ("orders", "payments", "messages"):
        tab = "orders"
    orders = storage.list_orders()
    payments = storage.list_payments()
    messages = storage.list_messages()
    return templates.TemplateResponse(request, "admin_orders.html", {
        "cart_count": get_cart_count(request),
        "tab": tab,
        "orders": orders,
        "payments": payments,
        "messages": messages,
        "order_statuses": storage.ORDER_STATUSES,
        "payment_statuses": storage.PAYMENT_STATUSES,
        "notify_channels": notify.enabled_channels(),
        "notify_email_ready": notify.EMAIL_READY,
        "notify_email_status": notify.email_status(),
        "notify_sms_ready": notify.SMS_READY,
        "notify_sms_status": notify.sms_status(),
        "notify_telegram_ready": notify.TELEGRAM_READY,
        "notify_telegram_status": notify.telegram_status(),
        "notify_test_ok": ntok,
        "notify_test_err": nterr,
        "counts": {
            "orders": len(orders),
            "payments": len(payments),
            "messages": len(messages),
            # ค้างรอตรวจ -> ใช้ขึ้นตัวเลขแดงเตือนบนแท็บ
            "pending": sum(1 for p in payments if p.get("status") == "pending"),
        },
    })


@protected.post("/notify/test")
async def notify_test():
    """ส่งข้อความทดสอบไปทุกช่องทางที่เปิดไว้ แล้วรายงานผลกลับหน้าแอดมิน"""
    ok, message = notify.send_test()
    key = "ntok" if ok else "nterr"
    return RedirectResponse(
        url=f"/admin/orders?{key}={quote(message)}", status_code=303
    )


@protected.post("/payment/review")
async def review_payment(
    payment_id: str = Form(...),
    action: str = Form(...),
    next: str = Form(None),
):
    """ยืนยันหรือปฏิเสธสลิป — คำสั่งซื้อที่ผูกไว้จะเปลี่ยนสถานะตามอัตโนมัติ"""
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="คำสั่งไม่ถูกต้อง")
    payment = storage.review_payment(payment_id, approve=action == "approve")
    if not payment:
        raise HTTPException(status_code=404, detail="ไม่พบรายการแจ้งชำระเงิน")
    order_no = payment.get("order_no")
    if order_no:
        order = storage.get_order(order_no)
        if order:
            notify.order_status_changed(order, storage.ORDER_STATUSES[order["status"]]["label"])
    target = safe_next(next) if next else "/admin/orders?tab=payments"
    return RedirectResponse(url=target, status_code=303)


@protected.get("/orders/{order_no}", response_class=HTMLResponse)
async def admin_order_detail(request: Request, order_no: str):
    """หน้ายืนยัน/รายละเอียดคำสั่งซื้อเดียว — ดูครบทุกอย่างและเปลี่ยนสถานะได้ในหน้าเดียว"""
    order = storage.get_order(order_no)
    if not order:
        raise HTTPException(status_code=404, detail="ไม่พบคำสั่งซื้อ")
    payments = [p for p in storage.list_payments() if p.get("order_no") == order["order_no"]]
    return templates.TemplateResponse(request, "admin_order_detail.html", {
        "cart_count": get_cart_count(request),
        "order": order,
        "payments": payments,
        "order_statuses": storage.ORDER_STATUSES,
        "payment_statuses": storage.PAYMENT_STATUSES,
    })


@protected.post("/order/status")
async def set_order_status(
    order_no: str = Form(...),
    status: str = Form(...),
    next: str = Form(None),
):
    """เปลี่ยนสถานะคำสั่งซื้อด้วยตนเอง (เช่น รับเงินสด/COD โดยไม่มีสลิป)"""
    order = storage.set_order_status(order_no, status)
    if not order:
        raise HTTPException(status_code=404, detail="ไม่พบคำสั่งซื้อหรือสถานะไม่ถูกต้อง")
    notify.order_status_changed(order, storage.ORDER_STATUSES[status]["label"])
    target = safe_next(next) if next else "/admin/orders?tab=orders"
    return RedirectResponse(url=target, status_code=303)


@protected.get("/slip/{filename}")
async def admin_slip(filename: str):
    """เปิดดูสลิปที่ลูกค้าอัปโหลด (ไฟล์อยู่นอก /static จึงเข้าถึงได้เฉพาะแอดมิน)"""
    path = storage.slip_path(filename)
    if not path:
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์สลิป")
    return FileResponse(path)


router.include_router(protected)

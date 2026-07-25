import re
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from core import templates
from data import (
    PRODUCTS, IMAGES_DIR, MAX_IMAGES, IMAGE_SLOTS,
    get_cart_count, set_product_image, remove_product_image, update_product,
)

router = APIRouter(prefix="/admin")

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _hex_or(value: str, fallback: str) -> str:
    """ตรวจสอบรหัสสี #rrggbb ถ้าไม่ถูกต้องใช้ค่าเดิม"""
    value = (value or "").strip()
    return value if _HEX_RE.match(value) else fallback


@router.get("/", response_class=HTMLResponse)
async def admin(request: Request, ok: int = None, error: str = None):
    return templates.TemplateResponse(request, "admin.html", {
        "products": PRODUCTS,
        "slots": IMAGE_SLOTS,
        "cart_count": get_cart_count(),
        "ok": ok,
        "error": error,
    })


@router.post("/upload")
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

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # ลบไฟล์เดิมในช่องนี้ (ถ้ามี) เพื่อไม่ให้ไฟล์ค้าง
    old = product["images"][slot] if slot < len(product["images"]) else None
    if old:
        (IMAGES_DIR / old).unlink(missing_ok=True)

    # ชื่อไฟล์ใหม่ระบุช่อง + timestamp -> เบราว์เซอร์โหลดรูปใหม่ทันที
    filename = f"product_{product_id}_s{slot}_{int(time.time())}{ext}"
    dest = IMAGES_DIR / filename
    with dest.open("wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    set_product_image(product_id, slot, filename)
    return RedirectResponse(url=f"/admin/?ok={product_id}", status_code=303)


@router.post("/update")
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


@router.post("/remove")
async def remove_image(product_id: int = Form(...), slot: int = Form(...)):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")

    old = product["images"][slot] if 0 <= slot < len(product["images"]) else None
    if old:
        (IMAGES_DIR / old).unlink(missing_ok=True)

    remove_product_image(product_id, slot)
    return RedirectResponse(url=f"/admin/?ok={product_id}", status_code=303)

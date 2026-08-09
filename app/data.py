import json
from datetime import date, timedelta
from pathlib import Path

from fastapi import Request

SIZES = ["S", "M", "L", "XL", "XXL"]

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "static" / "images" / "products"
_IMAGE_MAP = IMAGES_DIR / "_map.json"

MAX_IMAGES = 4
# ป้ายกำกับแต่ละช่องรูปในแกลเลอรี (ช่อง 0 = รูปหลัก แสดงทุกหน้า)
IMAGE_SLOTS = [
    {"label": "รูปหลัก", "hint": "แสดงทุกหน้า: โฮม · รายการสินค้า · ตะกร้า · แกลเลอรี"},
    {"label": "รูปที่ 2 — ด้านหลัง", "hint": "แสดงในแกลเลอรีหน้าสินค้า"},
    {"label": "รูปที่ 3 — รายละเอียดผ้า", "hint": "แสดงในแกลเลอรีหน้าสินค้า"},
    {"label": "รูปที่ 4 — ใส่จริง", "hint": "แสดงในแกลเลอรีหน้าสินค้า"},
]

# ไฟล์บันทึกรายละเอียดสินค้าที่แก้ผ่านแอดมิน (คงอยู่แม้รีสตาร์ท)
_PRODUCTS_FILE = BASE_DIR / "_products.json"
# ฟิลด์ที่แก้ไขได้จากหน้าแอดมิน พร้อมชนิดข้อมูล
EDITABLE_FIELDS = {
    "name": str, "brand": str, "subtitle": str, "type": str, "badge": str,
    "material": str, "care": str,
    "price": int, "old_price": int, "bulk10": int, "bulk50": int,
    "reviews_count": int, "sold": int, "stock": int,
    "rating": float,
    "c1": str, "c2": str, "c3": str,
    "features": list,
}

PRODUCTS = [
    {
        "id": 1,
        "name": "Strike SS",
        "brand": "Khunakorn",
        "subtitle": "Short Sleeve · Standard Series",
        "type": "short",
        "price": 199,
        "old_price": 259,
        "bulk10": 179, "bulk50": 159,
        "rating": 4.9, "reviews_count": 128, "sold": 1240, "stock": 37,
        "badge": "Best Value",
        "images": [None, None, None, None],
        "image": None,
        "c1": "#dc2626", "c2": "#991b1b", "c3": "#fca5a5",
        "features": ["DryFit 100%", "ระบายอากาศดีเยี่ยม", "น้ำหนักเบา", "ซักง่าย ไม่ยับ"],
        "material": "100% Polyester DryFit",
        "care": "Machine wash ≤ 30°C · No bleach",
    },
    {
        "id": 2,
        "name": "Elite SS",
        "brand": "Khunakorn",
        "subtitle": "Short Sleeve · Elite Series",
        "type": "short",
        "price": 299,
        "old_price": 379,
        "bulk10": 269, "bulk50": 239,
        "rating": 4.8, "reviews_count": 96, "sold": 870, "stock": 21,
        "badge": "Best Seller",
        "images": [None, None, None, None],
        "image": None,
        "c1": "#1d4ed8", "c2": "#1e3a8a", "c3": "#93c5fd",
        "features": ["AeroKnit™ พรีเมียม", "ระบายเหงื่อเทคโนโลยี", "Slim Fit", "ทอเนื้อแน่น"],
        "material": "88% Polyester · 12% Elastane AeroKnit™",
        "care": "Hand wash or delicate cycle · No tumble dry",
    },
    {
        "id": 3,
        "name": "Strike LS",
        "brand": "Khunakorn",
        "subtitle": "Long Sleeve · Standard Series",
        "type": "long",
        "price": 399,
        "old_price": 499,
        "bulk10": 369, "bulk50": 329,
        "rating": 4.9, "reviews_count": 64, "sold": 540, "stock": 44,
        "badge": "Recommended",
        "images": [None, None, None, None],
        "image": None,
        "c1": "#15803d", "c2": "#14532d", "c3": "#86efac",
        "features": ["UV Protection", "ThermoFit ผ้าหนาพิเศษ", "Ribbed cuffs", "เหมาะอากาศเย็น"],
        "material": "95% Polyester · 5% Spandex ThermoFit",
        "care": "Machine wash ≤ 30°C · Hang dry",
    },
    {
        "id": 4,
        "name": "Elite LS",
        "brand": "Khunakorn",
        "subtitle": "Long Sleeve · Elite Pro Series",
        "type": "long",
        "price": 499,
        "old_price": 629,
        "bulk10": 459, "bulk50": 419,
        "rating": 5.0, "reviews_count": 41, "sold": 320, "stock": 12,
        "badge": "Pro Series",
        "images": [None, None, None, None],
        "image": None,
        "c1": "#7e22ce", "c2": "#4c1d95", "c3": "#c4b5fd",
        "features": ["UltraKnit™ Pro", "ClimaCool Technology", "Athletic cut", "FIFA Quality Pro"],
        "material": "90% Polyester · 10% Elastane UltraKnit™",
        "care": "Hand wash only · No iron",
    },
]

# ── รีวิวตัวอย่าง (แก้เป็นรีวิวจริงของลูกค้าก่อนเปิดใช้งานจริง) ──
REVIEWS = {
    1: [
        {"name": "โค้ชสมชาย", "role": "ทีมโรงเรียน · กรุงเทพฯ", "stars": 5,
         "text": "สั่ง 40 ตัวให้ทีมนักเรียน ผ้าดีใส่สบาย ระบายอากาศดีมาก ส่งไว 2 วันถึง คุ้มราคาสุดๆ", "size": "L"},
        {"name": "ปุ๋ย ร้านกีฬา", "role": "ลูกค้าขายส่ง · นนทบุรี", "stars": 5,
         "text": "รับไปขายต่อ ลูกค้าชมเยอะ งานเนี้ยบ ตะเข็บแน่น สีไม่ตก จะสั่งเพิ่มเรื่อยๆ ครับ", "size": "M"},
    ],
    2: [
        {"name": "เอก ฟุตซอล", "role": "หัวหน้าทีม · ชลบุรี", "stars": 5,
         "text": "รุ่น Elite เนื้อผ้าพรีเมียมจริง Slim fit ทรงสวย ใส่แล้วดูโปร เพื่อนในทีมถามหาที่ซื้อกันหมด", "size": "L"},
        {"name": "มายด์", "role": "ลูกค้าทั่วไป · เชียงใหม่", "stars": 4,
         "text": "ผ้าดีมากค่ะ ระบายเหงื่อได้จริง ไซซ์พอดีตามตาราง แนะนำเลย", "size": "M"},
    ],
    3: [
        {"name": "โค้ชบอย", "role": "อคาเดมีเยาวชน · ขอนแก่น", "stars": 5,
         "text": "แขนยาวผ้าหนากำลังดี กันแดดได้ ซ้อมเช้าไม่ร้อน เด็กๆ ใส่แล้วชอบ สั่งยกทีมได้ราคาดีมาก", "size": "XL"},
    ],
    4: [
        {"name": "ต้น", "role": "ทีมสมัครเล่น · ภูเก็ต", "stars": 5,
         "text": "Pro Series คุณภาพระดับแข่งขันจริง ทรง Athletic ใส่วิ่งคล่อง คุ้มเกินราคา", "size": "L"},
    ],
}

_TH_MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
              "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def delivery_estimate(days: int = 2) -> str:
    """วันที่คาดว่าจะได้รับสินค้า (วันนี้ + N วัน) เป็นภาษาไทย"""
    d = date.today() + timedelta(days=days)
    return f"{d.day} {_TH_MONTHS[d.month - 1]} {d.year + 543}"


# ── ตะกร้าสินค้า (แยกตามผู้ใช้ เก็บใน session cookie) ──────
# เก็บเฉพาะ id/ไซซ์/จำนวน แล้วดึงชื่อ-ราคาจาก PRODUCTS ตอนแสดงผล
# -> cookie เล็ก และราคาตรงกับที่แอดมินตั้งไว้ล่าสุดเสมอ
_CART_KEY = "cart"
MAX_QTY = 999


def _raw_cart(request: Request) -> list[dict]:
    rows = request.session.get(_CART_KEY)
    return rows if isinstance(rows, list) else []


def _save_cart(request: Request, rows: list[dict]) -> None:
    if rows:
        request.session[_CART_KEY] = rows
    else:
        request.session.pop(_CART_KEY, None)


def _clean_qty(qty: int) -> int:
    return max(1, min(MAX_QTY, qty))


def get_cart_items(request: Request) -> list[dict]:
    """รายการในตะกร้าพร้อมข้อมูลสินค้าเต็ม (ข้ามสินค้าที่ถูกลบไปแล้ว)"""
    items = []
    for row in _raw_cart(request):
        product = next((p for p in PRODUCTS if p["id"] == row.get("pid")), None)
        if not product:
            continue
        qty = _clean_qty(int(row.get("qty", 1)))
        items.append({
            "key": f"{product['id']}_{row.get('size', 'M')}",
            "product_id": product["id"],
            "name": f"{product['brand']} {product['name']}",
            "price": product["price"],
            "size": row.get("size", "M"),
            "qty": qty,
            "subtotal": product["price"] * qty,
            "c1": product["c1"],
            "c2": product["c2"],
            "type": product["type"],
            "image": product.get("image"),
        })
    return items


def get_cart_count(request: Request) -> int:
    return sum(i["qty"] for i in get_cart_items(request))


def get_cart_total(request: Request) -> int:
    return sum(i["subtotal"] for i in get_cart_items(request))


def add_to_cart(request: Request, product_id: int, size: str, qty: int) -> bool:
    """เพิ่มสินค้าลงตะกร้า คืน False ถ้าไม่พบสินค้า"""
    if not any(p["id"] == product_id for p in PRODUCTS):
        return False
    if size not in SIZES:
        size = "M"
    qty = _clean_qty(qty)

    rows = _raw_cart(request)
    for row in rows:
        if row.get("pid") == product_id and row.get("size") == size:
            row["qty"] = _clean_qty(int(row.get("qty", 1)) + qty)
            break
    else:
        rows.append({"pid": product_id, "size": size, "qty": qty})
    _save_cart(request, rows)
    return True


def update_cart_item(request: Request, key: str, qty: int) -> None:
    """แก้จำนวนสินค้าตาม key — จำนวน <= 0 คือลบออกจากตะกร้า"""
    if qty <= 0:
        remove_cart_item(request, key)
        return
    rows = _raw_cart(request)
    for row in rows:
        if f"{row.get('pid')}_{row.get('size')}" == key:
            row["qty"] = _clean_qty(qty)
    _save_cart(request, rows)


def remove_cart_item(request: Request, key: str) -> None:
    rows = [r for r in _raw_cart(request)
            if f"{r.get('pid')}_{r.get('size')}" != key]
    _save_cart(request, rows)


def clear_cart(request: Request) -> None:
    request.session.pop(_CART_KEY, None)


def _sync_main(p: dict) -> None:
    """รูปหลัก = รูปแรกที่ไม่ว่างในแกลเลอรี (ให้หน้าอื่นที่ใช้ p['image'] ทำงานต่อได้)"""
    p["image"] = next((f for f in p["images"] if f), None)


def _save_images() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    mapping = {str(p["id"]): p["images"] for p in PRODUCTS if any(p["images"])}
    _IMAGE_MAP.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_images() -> None:
    """โหลดรายการรูปที่เคยอัปโหลดไว้ (คงอยู่แม้รีสตาร์ทเซิร์ฟเวอร์)"""
    if not _IMAGE_MAP.exists():
        return
    try:
        mapping = json.loads(_IMAGE_MAP.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return
    for p in PRODUCTS:
        val = mapping.get(str(p["id"]))
        if not val:
            continue
        if isinstance(val, str):  # รองรับข้อมูลรูปแบบเก่า (รูปเดียว)
            val = [val]
        imgs = [None] * MAX_IMAGES
        for i, fn in enumerate(val[:MAX_IMAGES]):
            if fn and (IMAGES_DIR / fn).exists():
                imgs[i] = fn
        p["images"] = imgs
        _sync_main(p)


def set_product_image(product_id: int, slot: int, filename: str) -> None:
    """ตั้งรูปในช่อง slot ของสินค้า แล้วบันทึก"""
    for p in PRODUCTS:
        if p["id"] == product_id and 0 <= slot < MAX_IMAGES:
            while len(p["images"]) < MAX_IMAGES:
                p["images"].append(None)
            p["images"][slot] = filename
            _sync_main(p)
    _save_images()


def remove_product_image(product_id: int, slot: int) -> None:
    """ลบรูปในช่อง slot ของสินค้า แล้วบันทึก"""
    for p in PRODUCTS:
        if p["id"] == product_id and 0 <= slot < len(p["images"]):
            p["images"][slot] = None
            _sync_main(p)
    _save_images()


def _save_products() -> None:
    """บันทึกรายละเอียดสินค้าทั้งหมด (เฉพาะฟิลด์ที่แก้ได้) ลงไฟล์"""
    overrides = {
        str(p["id"]): {k: p[k] for k in EDITABLE_FIELDS if k in p}
        for p in PRODUCTS
    }
    _PRODUCTS_FILE.write_text(
        json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_products() -> None:
    """โหลดรายละเอียดสินค้าที่แก้ไว้ มาทับค่าเริ่มต้น"""
    if not _PRODUCTS_FILE.exists():
        return
    try:
        overrides = json.loads(_PRODUCTS_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return
    for p in PRODUCTS:
        ov = overrides.get(str(p["id"]))
        if not ov:
            continue
        for k, v in ov.items():
            if k in EDITABLE_FIELDS:
                p[k] = v


def update_product(product_id: int, fields: dict) -> None:
    """อัปเดตรายละเอียดสินค้า (เฉพาะฟิลด์ที่อนุญาต) แล้วบันทึก"""
    for p in PRODUCTS:
        if p["id"] == product_id:
            for k, v in fields.items():
                if k in EDITABLE_FIELDS:
                    p[k] = v
    _save_products()


_load_products()
_load_images()

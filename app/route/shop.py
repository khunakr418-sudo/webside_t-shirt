from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

from core import templates
from data import PRODUCTS, SIZES, get_cart_count

router = APIRouter(prefix="/shop")


@router.get("/", response_class=HTMLResponse)
async def shop(request: Request, filter_type: Optional[str] = None):
    products = PRODUCTS if filter_type not in ("short", "long") else [p for p in PRODUCTS if p["type"] == filter_type]
    return templates.TemplateResponse(request, "shop.html", {
        "products": products,
        "filter_type": filter_type,
        "cart_count": get_cart_count(),
    })


@router.get("/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: int):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    return templates.TemplateResponse(request, "product.html", {
        "product": product,
        "sizes": SIZES,
        "cart_count": get_cart_count(),
    })

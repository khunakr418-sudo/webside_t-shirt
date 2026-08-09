from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from core import templates
from data import (
    add_to_cart, get_cart_items, remove_cart_item, update_cart_item,
)

router = APIRouter(prefix="/cart")


@router.get("/", response_class=HTMLResponse)
async def view_cart(request: Request):
    items = get_cart_items(request)
    return templates.TemplateResponse(request, "cart.html", {
        "cart": items,
        "cart_count": sum(i["qty"] for i in items),
        "total": sum(i["subtotal"] for i in items),
        "product_images": {i["product_id"]: i["image"] for i in items},
    })


@router.post("/add")
async def add_item(
    request: Request,
    product_id: int = Form(...),
    qty: int = Form(default=1),
    size: str = Form(default="M"),
):
    if not add_to_cart(request, product_id, size, qty):
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    return RedirectResponse(url="/cart/", status_code=303)


@router.post("/update")
async def update_cart(request: Request, key: str = Form(...), qty: int = Form(...)):
    update_cart_item(request, key, qty)
    return RedirectResponse(url="/cart/", status_code=303)


@router.post("/remove")
async def remove_from_cart(request: Request, key: str = Form(...)):
    remove_cart_item(request, key)
    return RedirectResponse(url="/cart/", status_code=303)

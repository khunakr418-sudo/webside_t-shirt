from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from core import templates
from data import PRODUCTS, cart, get_cart_count, get_cart_total

router = APIRouter(prefix="/cart")


@router.get("/", response_class=HTMLResponse)
async def view_cart(request: Request):
    return templates.TemplateResponse(request, "cart.html", {
        "cart": cart,
        "cart_count": get_cart_count(),
        "total": get_cart_total(),
    })


@router.post("/add")
async def add_to_cart(
    product_id: int = Form(...),
    qty: int = Form(default=1),
    size: str = Form(default="M"),
):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404)
    key = f"{product_id}_{size}"
    existing = next((i for i in cart if i["key"] == key), None)
    if existing:
        existing["qty"] += qty
    else:
        cart.append({
            "key": key,
            "product_id": product_id,
            "name": f"{product['brand']} {product['name']}",
            "price": product["price"],
            "size": size,
            "qty": qty,
            "c1": product["c1"],
            "c2": product["c2"],
            "type": product["type"],
        })
    return RedirectResponse(url="/cart/", status_code=303)


@router.post("/update")
async def update_cart(key: str = Form(...), qty: int = Form(...)):
    if qty <= 0:
        cart[:] = [i for i in cart if i["key"] != key]
    else:
        item = next((i for i in cart if i["key"] == key), None)
        if item:
            item["qty"] = qty
    return RedirectResponse(url="/cart/", status_code=303)


@router.post("/remove")
async def remove_from_cart(key: str = Form(...)):
    cart[:] = [i for i in cart if i["key"] != key]
    return RedirectResponse(url="/cart/", status_code=303)

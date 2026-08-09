from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

import notify
import storage
from core import templates
from data import clear_cart, get_cart_count, get_cart_items

router = APIRouter(prefix="/order")

_LAST_ORDER_KEY = "last_order_no"
_MY_ORDERS_KEY = "my_orders"
MAX_TRACKED_ORDERS = 10


def remember_order(request: Request, order_no: str) -> None:
    """จำเลขที่คำสั่งซื้อไว้ใน session เพื่อให้หน้าแจ้งชำระเงินเลือกได้เลย"""
    tracked = request.session.get(_MY_ORDERS_KEY)
    tracked = tracked if isinstance(tracked, list) else []
    if order_no not in tracked:
        tracked.append(order_no)
    request.session[_MY_ORDERS_KEY] = tracked[-MAX_TRACKED_ORDERS:]


def my_order_numbers(request: Request) -> list[str]:
    tracked = request.session.get(_MY_ORDERS_KEY)
    return [n for n in tracked if isinstance(n, str)] if isinstance(tracked, list) else []


@router.get("/checkout", response_class=HTMLResponse)
async def checkout(request: Request):
    items = get_cart_items(request)
    if not items:
        return RedirectResponse(url="/cart/", status_code=303)
    return templates.TemplateResponse(request, "checkout.html", {
        "cart": items,
        "cart_count": sum(i["qty"] for i in items),
        "total": sum(i["subtotal"] for i in items),
    })


@router.post("/confirm")
async def confirm_order(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
):
    items = get_cart_items(request)
    if not items:
        return RedirectResponse(url="/cart/", status_code=303)

    order = storage.save_order(
        customer={
            "name": name.strip(),
            "phone": phone.strip(),
            "address": address.strip(),
        },
        items=items,
        total=sum(i["subtotal"] for i in items),
    )

    clear_cart(request)
    # เก็บเลขที่ออเดอร์ไว้ใน session ให้หน้าสำเร็จอ่าน (ไม่ส่งผ่าน URL)
    request.session[_LAST_ORDER_KEY] = order["order_no"]
    remember_order(request, order["order_no"])
    notify.new_order(order)
    return RedirectResponse(url="/order/success", status_code=303)


@router.get("/success", response_class=HTMLResponse)
async def order_success(request: Request):
    order_no = request.session.pop(_LAST_ORDER_KEY, None)
    order = storage.get_order(order_no) if order_no else None
    return templates.TemplateResponse(request, "success.html", {
        "cart_count": get_cart_count(request),
        "order": order,
    })

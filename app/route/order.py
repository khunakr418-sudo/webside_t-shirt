from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from core import templates
from data import cart, get_cart_count, get_cart_total

router = APIRouter(prefix="/order")


@router.get("/checkout", response_class=HTMLResponse)
async def checkout(request: Request):
    if not cart:
        return RedirectResponse(url="/cart/", status_code=303)
    return templates.TemplateResponse(request, "checkout.html", {
        "cart": cart,
        "cart_count": get_cart_count(),
        "total": get_cart_total(),
    })


@router.post("/confirm")
async def confirm_order(
    name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
):
    cart.clear()
    return RedirectResponse(url="/order/success", status_code=303)


@router.get("/success", response_class=HTMLResponse)
async def order_success(request: Request):
    return templates.TemplateResponse(request, "success.html", {"cart_count": 0})

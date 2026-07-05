from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from core import templates
from data import PRODUCTS, get_cart_count

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(request, "landing.html", {
        "products": PRODUCTS,
        "cart_count": get_cart_count(),
    })

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

import storage
from core import templates
from data import get_cart_count

router = APIRouter(prefix="/contact")


@router.get("/", response_class=HTMLResponse)
async def contact(request: Request, sent: int = 0):
    return templates.TemplateResponse(request, "contact.html", {
        "cart_count": get_cart_count(request),
        "sent": bool(sent),
    })


@router.post("/send")
async def contact_send(
    name: str = Form(...),
    contact: str = Form(...),
    topic: str = Form("ทั่วไป"),
    message: str = Form(...),
):
    storage.save_message(
        name=name.strip(),
        contact=contact.strip(),
        topic=topic.strip() or "ทั่วไป",
        message=message.strip(),
    )
    return RedirectResponse(url="/contact/?sent=1#form", status_code=303)

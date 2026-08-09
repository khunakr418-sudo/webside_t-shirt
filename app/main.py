import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import config
from route import landing, shop, cart, order, contact, payment, admin

app = FastAPI(title="Khunakorn Football Shop")

# ตะกร้าสินค้าและการล็อกอินแอดมินเก็บใน cookie ที่เซ็นชื่อกำกับไว้
app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    session_cookie="ks_session",
    max_age=config.SESSION_MAX_AGE,
    same_site="lax",
    https_only=False,   # production ที่ใช้ HTTPS ให้เปลี่ยนเป็น True
)

_BASE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")

app.include_router(landing)
app.include_router(shop)
app.include_router(cart)
app.include_router(order)
app.include_router(contact)
app.include_router(payment)
app.include_router(admin)

# แจ้งรหัสผ่านแอดมินทางคอนโซล (flush เพราะ stdout ถูกบัฟเฟอร์เมื่อไม่ได้ต่อกับ terminal)
_banner = config.startup_banner()
if _banner:
    print(_banner, flush=True)

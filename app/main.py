import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from route import landing, shop, cart, order

app = FastAPI(title="Khunakorn Football Shop")

_BASE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")

app.include_router(landing)
app.include_router(shop)
app.include_router(cart)
app.include_router(order)

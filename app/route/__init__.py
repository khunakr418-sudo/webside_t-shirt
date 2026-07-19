from .landing import router as landing
from .shop import router as shop
from .cart import router as cart
from .order import router as order
from .contact import router as contact
from .payment import router as payment

__all__ = ["landing", "shop", "cart", "order", "contact", "payment"]

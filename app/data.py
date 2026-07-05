SIZES = ["S", "M", "L", "XL", "XXL"]

PRODUCTS = [
    {
        "id": 1,
        "name": "Strike SS",
        "brand": "Khunakorn",
        "subtitle": "Short Sleeve · Standard Series",
        "type": "short",
        "price": 199,
        "badge": "Best Value",
        "c1": "#dc2626", "c2": "#991b1b", "c3": "#fca5a5",
        "features": ["DryFit 100%", "ระบายอากาศดีเยี่ยม", "น้ำหนักเบา", "ซักง่าย ไม่ยับ"],
        "material": "100% Polyester DryFit",
        "care": "Machine wash ≤ 30°C · No bleach",
    },
    {
        "id": 2,
        "name": "Elite SS",
        "brand": "Khunakorn",
        "subtitle": "Short Sleeve · Elite Series",
        "type": "short",
        "price": 299,
        "badge": "Best Seller",
        "c1": "#1d4ed8", "c2": "#1e3a8a", "c3": "#93c5fd",
        "features": ["AeroKnit™ พรีเมียม", "ระบายเหงื่อเทคโนโลยี", "Slim Fit", "ทอเนื้อแน่น"],
        "material": "88% Polyester · 12% Elastane AeroKnit™",
        "care": "Hand wash or delicate cycle · No tumble dry",
    },
    {
        "id": 3,
        "name": "Strike LS",
        "brand": "Khunakorn",
        "subtitle": "Long Sleeve · Standard Series",
        "type": "long",
        "price": 399,
        "badge": "Recommended",
        "c1": "#15803d", "c2": "#14532d", "c3": "#86efac",
        "features": ["UV Protection", "ThermoFit ผ้าหนาพิเศษ", "Ribbed cuffs", "เหมาะอากาศเย็น"],
        "material": "95% Polyester · 5% Spandex ThermoFit",
        "care": "Machine wash ≤ 30°C · Hang dry",
    },
    {
        "id": 4,
        "name": "Elite LS",
        "brand": "Khunakorn",
        "subtitle": "Long Sleeve · Elite Pro Series",
        "type": "long",
        "price": 499,
        "badge": "Pro Series",
        "c1": "#7e22ce", "c2": "#4c1d95", "c3": "#c4b5fd",
        "features": ["UltraKnit™ Pro", "ClimaCool Technology", "Athletic cut", "FIFA Quality Pro"],
        "material": "90% Polyester · 10% Elastane UltraKnit™",
        "care": "Hand wash only · No iron",
    },
]

cart: list[dict] = []


def get_cart_count() -> int:
    return sum(i["qty"] for i in cart)


def get_cart_total() -> int:
    return sum(i["price"] * i["qty"] for i in cart)

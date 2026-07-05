# ⚽ ProKit Football Shop

ร้านขายส่งเสื้อฟุตบอลออนไลน์ สร้างด้วย **FastAPI + Jinja2**

## Tech Stack

- **Backend:** FastAPI (Python)
- **Templates:** Jinja2
- **Styling:** Custom CSS (no framework)
- **Server:** Uvicorn

## Project Structure

```
football_shop/
├── main.py              # FastAPI app entry point
├── core.py              # Shared Jinja2Templates instance
├── data.py              # Product data & cart state
├── route/
│   ├── __init__.py      # Exports all routers
│   ├── landing.py       # GET /
│   ├── shop.py          # GET /shop/  GET /shop/{id}
│   ├── cart.py          # GET /cart/  POST /cart/add|update|remove
│   └── order.py         # GET /order/checkout  POST /order/confirm
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── shop.html
│   ├── product.html
│   ├── cart.html
│   ├── checkout.html
│   ├── success.html
│   └── partials/
│       ├── jersey.html  # SVG jersey macro
│       └── footbar.html
└── static/
    └── css/
        └── style.css
```

## Getting Started

**1. Clone the repo**
```bash
git clone https://github.com/khunakr418-sudo/python.git
cd python
```

**2. Create virtual environment**
```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Run the server**
```bash
cd football_shop
uvicorn main:app --reload
```

**5. Open in browser**
```
http://127.0.0.1:8000
```

## Pages

| URL | Description |
|---|---|
| `/` | Landing page |
| `/shop/` | Product listing |
| `/shop/{id}` | Product detail |
| `/cart/` | Shopping cart |
| `/order/checkout` | Checkout form |
| `/order/success` | Order confirmation |

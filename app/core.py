from pathlib import Path
from fastapi.templating import Jinja2Templates

import config

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ข้อมูลติดต่อร้าน ใช้ได้ทุกเทมเพลตโดยไม่ต้องส่งผ่าน context ทีละหน้า
templates.env.globals["shop"] = {
    "email": config.SHOP_EMAIL,
    "phone": config.SHOP_PHONE_DISPLAY,
    "phone_link": config.SHOP_PHONE_LINK,
    "hours": config.SHOP_HOURS,
}

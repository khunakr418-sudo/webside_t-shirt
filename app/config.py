"""ค่าตั้งค่าและความลับของระบบ (secret key / รหัสผ่านแอดมิน)

ลำดับการอ่านค่า: ตัวแปรสภาพแวดล้อม (env) มาก่อนเสมอ
ถ้าไม่ได้ตั้ง env ไว้ ระบบจะสร้างค่าสุ่มเก็บใน _data/secrets.json ให้อัตโนมัติ
(ไฟล์นี้อยู่ใน .gitignore — ห้าม commit)
"""

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "_data"
_SECRETS_FILE = DATA_DIR / "secrets.json"

# อายุ session ของลูกค้า (ตะกร้า) และของแอดมิน
SESSION_MAX_AGE = 14 * 24 * 3600      # 14 วัน
ADMIN_SESSION_MAX_AGE = 8 * 3600      # 8 ชั่วโมง

_PBKDF2_ROUNDS = 200_000

# ── ข้อมูลติดต่อร้าน ──────────────────────────────────────
# ใช้ทั้งแสดงบนเว็บ และเป็นปลายทางแจ้งเตือนของผู้ขาย
SHOP_EMAIL = os.getenv("SHOP_EMAIL", "").strip() or "khunakr418@gmail.com"
SHOP_PHONE = os.getenv("SHOP_PHONE", "").strip() or "0849948889"
SHOP_HOURS = os.getenv("SHOP_HOURS", "").strip() or "จ–ศ 09:00–18:00 น."


def _phone_digits(phone: str) -> str:
    return "".join(c for c in phone if c.isdigit())


def _phone_display(phone: str) -> str:
    """จัดรูปเบอร์มือถือไทยให้อ่านง่าย: 0849948889 -> 084-994-8889"""
    d = _phone_digits(phone)
    if len(d) == 10 and d.startswith("0"):
        return f"{d[:3]}-{d[3:6]}-{d[6:]}"
    if len(d) == 9 and d.startswith("0"):     # เบอร์บ้าน เช่น 021234567
        return f"{d[:2]}-{d[2:5]}-{d[5:]}"
    return phone


SHOP_PHONE_DISPLAY = _phone_display(SHOP_PHONE)
SHOP_PHONE_LINK = _phone_digits(SHOP_PHONE)


def hash_password(password: str) -> str:
    """แปลงรหัสผ่านเป็น pbkdf2_sha256$<rounds>$<salt>$<hash>"""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """ตรวจรหัสผ่านแบบ constant-time (กัน timing attack)"""
    try:
        algo, rounds, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(dk.hex(), hash_hex)


def _read_local_secrets() -> dict:
    if not _SECRETS_FILE.exists():
        return {}
    try:
        return json.loads(_SECRETS_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def _write_local_secrets(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _SECRETS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _smtp_from_local(local: dict) -> dict:
    """ตั้งค่าอีเมลแจ้งเตือน — env มาก่อน แล้วค่อยอ่านจาก secrets.json

    ค่าเริ่มต้นตั้งไว้ให้ Gmail ของร้านแล้ว เหลือแค่ใส่ App Password
    (Gmail ใช้รหัสผ่านปกติส่งไม่ได้ ต้องสร้าง App Password 16 หลัก)
    """
    block = local.get("smtp") if isinstance(local.get("smtp"), dict) else {}
    # Google แสดง App Password เป็น 4 กลุ่มมีเว้นวรรค — ตัดช่องว่างให้ วางมาแบบไหนก็ใช้ได้
    password = (os.getenv("SMTP_PASS") or block.get("app_password") or "")
    return {
        "host": os.getenv("SMTP_HOST") or block.get("host") or "smtp.gmail.com",
        "port": int(os.getenv("SMTP_PORT") or block.get("port") or 587),
        "user": os.getenv("SMTP_USER") or block.get("user") or SHOP_EMAIL,
        "password": "".join(password.split()),
        "sender": os.getenv("SMTP_FROM") or block.get("from") or SHOP_EMAIL,
        "to": os.getenv("SMTP_TO") or block.get("to") or SHOP_EMAIL,
    }


def _sms_from_local(local: dict) -> dict:
    """ตั้งค่า SMS แจ้งเตือน — env มาก่อน แล้วค่อยอ่านจาก secrets.json

    รองรับ ThaiBulkSMS (ค่าเริ่มต้น) และ Twilio
    ต้องสมัครบริการและเติมเงินเอง แล้วนำ API key มาใส่
    """
    block = local.get("sms") if isinstance(local.get("sms"), dict) else {}
    return {
        "provider": (os.getenv("SMS_PROVIDER") or block.get("provider")
                     or "thaibulksms").lower(),
        "to": os.getenv("SMS_TO") or block.get("to") or SHOP_PHONE,
        "sender": os.getenv("SMS_SENDER") or block.get("sender") or "",
        "key": os.getenv("SMS_API_KEY") or block.get("api_key") or "",
        "secret": os.getenv("SMS_API_SECRET") or block.get("api_secret") or "",
    }


def _load() -> tuple[str, str, str, str | None]:
    """คืน (secret_key, admin_user, admin_password_hash, รหัสผ่านที่เก็บในไฟล์)

    ลำดับความสำคัญของรหัสผ่าน:
      1. env ADMIN_PASSWORD_HASH  (แนะนำสำหรับ production)
      2. env ADMIN_PASSWORD
      3. ไฟล์ _data/secrets.json  (แก้ไฟล์นี้เพื่อเปลี่ยนรหัสผ่านได้เลย)
      4. สุ่มให้ใหม่ ถ้ายังไม่มีที่ไหนเลย
    """
    local = _read_local_secrets()
    dirty = False
    local_password: str | None = None

    secret_key = os.getenv("SECRET_KEY") or local.get("secret_key")
    if not secret_key:
        secret_key = secrets.token_urlsafe(48)
        local["secret_key"] = secret_key
        dirty = True

    admin_user = os.getenv("ADMIN_USER") or local.get("admin_user") or "admin"

    pw_hash = os.getenv("ADMIN_PASSWORD_HASH")
    env_password = os.getenv("ADMIN_PASSWORD")
    if not pw_hash and env_password:
        pw_hash = hash_password(env_password)

    if not pw_hash:
        local_password = local.get("admin_password")
        if not local_password:
            # ยังไม่เคยตั้งรหัสผ่านที่ไหนเลย -> สุ่มให้ใหม่
            local_password = secrets.token_urlsafe(9)
            dirty = True
        # เก็บรหัสผ่านไว้ในไฟล์เพื่อให้เจ้าของร้านเปิดดู/แก้ไขได้
        # (ไฟล์อยู่ใน .gitignore — production ควรใช้ env แทน)
        local["admin_user"] = admin_user
        local["admin_password"] = local_password
        local["_note"] = (
            "ห้าม commit ไฟล์นี้ขึ้น git · "
            "เปลี่ยนรหัสผ่านแอดมินได้โดยแก้ค่า admin_password แล้วรีสตาร์ทเซิร์ฟเวอร์ · "
            "production ให้ตั้ง env SECRET_KEY และ ADMIN_PASSWORD_HASH แทน"
        )
        local.pop("admin_password_hash", None)
        pw_hash = hash_password(local_password)

    # เขียนโครงตั้งค่าอีเมลไว้ให้ เจ้าของร้านมาเติม App Password เองภายหลัง
    if not isinstance(local.get("smtp"), dict):
        local["smtp"] = {
            "_howto": (
                "ส่งอีเมลแจ้งเตือน: ใส่ App Password ของ Gmail ในช่อง app_password "
                "(สร้างที่ https://myaccount.google.com/apppasswords "
                "ต้องเปิด 2-Step Verification ก่อน) แล้วรีสตาร์ทเซิร์ฟเวอร์"
            ),
            "host": "smtp.gmail.com",
            "port": 587,
            "user": SHOP_EMAIL,
            "app_password": "",
            "from": SHOP_EMAIL,
            "to": SHOP_EMAIL,
        }
        dirty = True

    # โครงตั้งค่า SMS — ต้องสมัครบริการเองแล้วนำ API key มาใส่
    if not isinstance(local.get("sms"), dict):
        local["sms"] = {
            "_howto": (
                "ส่ง SMS แจ้งเตือน: สมัคร ThaiBulkSMS (thaibulksms.com) หรือ Twilio "
                "แล้วนำ API key/secret มาใส่ · provider ใส่ 'thaibulksms' หรือ 'twilio' · "
                "sender คือชื่อผู้ส่งที่ลงทะเบียนไว้ (Twilio ใช้เบอร์ต้นทาง) · "
                "SMS ภาษาไทยคิด 70 ตัวอักษรต่อ 1 ข้อความ · แล้วรีสตาร์ทเซิร์ฟเวอร์"
            ),
            "provider": "thaibulksms",
            "to": SHOP_PHONE,
            "sender": "",
            "api_key": "",
            "api_secret": "",
        }
        dirty = True

    if dirty:
        _write_local_secrets(local)

    return secret_key, admin_user, pw_hash, local_password


SECRET_KEY, ADMIN_USER, ADMIN_PASSWORD_HASH, LOCAL_PASSWORD = _load()
_local = _read_local_secrets()
SMTP = _smtp_from_local(_local)
SMS = _sms_from_local(_local)


def _console_supports_thai() -> bool:
    """คอนโซล Windows ส่วนใหญ่แสดงภาษาไทยไม่ได้ — ตรวจก่อนว่าพิมพ์ออกมาแล้วอ่านรู้เรื่อง"""
    import sys
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        "ทดสอบ".encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return encoding.lower().replace("-", "") in ("utf8", "utf16", "utf32")


def startup_banner() -> str | None:
    """ข้อความแจ้งรหัสผ่านแอดมิน แสดงเมื่อยังใช้รหัสผ่านจากไฟล์ (ไม่ได้ตั้ง env)"""
    if not LOCAL_PASSWORD:
        return None

    if _console_supports_thai():
        lines = [
            "  บัญชีผู้ดูแลระบบ (ยังไม่ได้ตั้ง env ADMIN_PASSWORD)",
            "    เข้าสู่ระบบที่ : /admin/login",
            f"    ชื่อผู้ใช้     : {ADMIN_USER}",
            f"    รหัสผ่าน      : {LOCAL_PASSWORD}",
            f"  เก็บไว้ที่ {_SECRETS_FILE}",
            "  (แก้ค่า admin_password ในไฟล์นั้นเพื่อเปลี่ยนรหัสผ่าน)",
            "  production: ตั้ง env SECRET_KEY / ADMIN_USER / ADMIN_PASSWORD_HASH",
        ]
    else:
        lines = [
            "  ADMIN LOGIN (env ADMIN_PASSWORD is not set)",
            "    url      : /admin/login",
            f"    username : {ADMIN_USER}",
            f"    password : {LOCAL_PASSWORD}",
            f"  stored in {_SECRETS_FILE}",
            "  (edit admin_password in that file to change it)",
            "  production: set env SECRET_KEY / ADMIN_USER / ADMIN_PASSWORD_HASH",
        ]

    bar = "=" * 66
    return "\n" + bar + "\n" + "\n".join(lines) + "\n" + bar + "\n"

"""ระบบยืนยันตัวตนของแอดมิน (session + จำกัดจำนวนครั้งที่ล็อกอินผิด)"""

import time

from fastapi import HTTPException, Request

from config import (
    ADMIN_PASSWORD_HASH, ADMIN_SESSION_MAX_AGE, ADMIN_USER, verify_password,
)

_SESSION_KEY = "admin_since"

# กันเดารหัสผ่าน: ผิดครบ MAX_ATTEMPTS ครั้ง จะล็อก IP นั้นไว้ LOCKOUT วินาที
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60
_attempts: dict[str, tuple[int, float]] = {}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def lockout_remaining(request: Request) -> int:
    """เหลืออีกกี่วินาทีถึงจะลองล็อกอินใหม่ได้ (0 = ลองได้เลย)"""
    count, last = _attempts.get(_client_ip(request), (0, 0.0))
    if count < MAX_ATTEMPTS:
        return 0
    remaining = int(last + LOCKOUT_SECONDS - time.time())
    return max(0, remaining)


def record_failure(request: Request) -> None:
    ip = _client_ip(request)
    count, last = _attempts.get(ip, (0, 0.0))
    # ถ้าเลยเวลาล็อกไปแล้ว เริ่มนับใหม่
    if count >= MAX_ATTEMPTS and time.time() > last + LOCKOUT_SECONDS:
        count = 0
    _attempts[ip] = (count + 1, time.time())


def reset_failures(request: Request) -> None:
    _attempts.pop(_client_ip(request), None)


def check_credentials(username: str, password: str) -> bool:
    """ตรวจชื่อผู้ใช้และรหัสผ่าน (ตรวจรหัสผ่านเสมอเพื่อให้เวลาตอบสนองคงที่)"""
    ok_password = verify_password(password, ADMIN_PASSWORD_HASH)
    return ok_password and username.strip() == ADMIN_USER


def login_admin(request: Request) -> None:
    request.session[_SESSION_KEY] = int(time.time())


def logout_admin(request: Request) -> None:
    request.session.pop(_SESSION_KEY, None)


def is_admin(request: Request) -> bool:
    since = request.session.get(_SESSION_KEY)
    if not isinstance(since, int):
        return False
    if time.time() - since > ADMIN_SESSION_MAX_AGE:
        request.session.pop(_SESSION_KEY, None)
        return False
    return True


def safe_next(target: str | None) -> str:
    """อนุญาตให้ redirect กลับได้เฉพาะเส้นทางภายใน /admin (กัน open redirect)"""
    if not target or not target.startswith("/admin") or target.startswith("//"):
        return "/admin/"
    return target


async def require_admin(request: Request) -> None:
    """Dependency: ถ้ายังไม่ล็อกอิน ให้เด้งไปหน้าล็อกอิน"""
    if is_admin(request):
        return
    nxt = safe_next(request.url.path)
    raise HTTPException(
        status_code=303,
        detail="ต้องเข้าสู่ระบบก่อน",
        headers={"Location": f"/admin/login?next={nxt}"},
    )

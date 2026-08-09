"""แจ้งเตือนร้านเมื่อมีคำสั่งซื้อใหม่ / มีการแจ้งชำระเงิน

รองรับ 4 ช่องทาง เปิดช่องไหนก็ได้ ไม่ตั้งก็ไม่ส่ง:

  1) Webhook  env NOTIFY_WEBHOOK_URL     Discord / Slack / n8n / Make
  2) LINE     env LINE_CHANNEL_TOKEN     ผ่าน Messaging API (broadcast)
  3) อีเมล     ส่วน smtp ใน secrets.json  (หรือ env SMTP_*)
  4) SMS      ส่วน sms ใน secrets.json   ThaiBulkSMS / Twilio — มีค่าใช้จ่าย

หมายเหตุ: LINE Notify ปิดให้บริการไปแล้วเมื่อ 31 มี.ค. 2568
จึงใช้ LINE Messaging API (ช่อง OA) แทน

SMS ภาษาไทยคิด 70 ตัวอักษรต่อข้อความ จึงส่งเฉพาะใจความสั้น
ส่วนรายละเอียดเต็มไปทางอีเมล/webhook

ส่งแบบเบื้องหลังเสมอ — ถ้าปลายทางล่มหรือช้า จะไม่กระทบการสั่งซื้อของลูกค้า
"""

import base64
import json
import os
import smtplib
import ssl
import threading
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage

import config

TIMEOUT = 8  # วินาที

WEBHOOK_URL = os.getenv("NOTIFY_WEBHOOK_URL", "").strip()
LINE_TOKEN = os.getenv("LINE_CHANNEL_TOKEN", "").strip()

# ตั้งค่าอีเมลอ่านจาก config (env -> _data/secrets.json)
SMTP_HOST = config.SMTP["host"]
SMTP_PORT = config.SMTP["port"]
SMTP_USER = config.SMTP["user"]
SMTP_PASS = config.SMTP["password"]
SMTP_FROM = config.SMTP["sender"]
SMTP_TO = config.SMTP["to"]

# เว็บไซต์ของร้าน ใช้ทำลิงก์ในข้อความแจ้งเตือน
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000").rstrip("/")

# ต้องมีรหัสผ่านถึงจะส่งได้ (Gmail และผู้ให้บริการส่วนใหญ่บังคับล็อกอิน)
EMAIL_READY = bool(SMTP_HOST and SMTP_TO and SMTP_PASS)

# ตั้งค่า SMS อ่านจาก config (env -> _data/secrets.json)
SMS = config.SMS
SMS_READY = bool(SMS["key"] and SMS["to"])


def enabled_channels() -> list[str]:
    """ช่องทางที่ตั้งค่าไว้แล้ว — ใช้แสดงสถานะในหน้าแอดมิน"""
    channels = []
    if WEBHOOK_URL:
        channels.append("Webhook")
    if LINE_TOKEN:
        channels.append("LINE")
    if EMAIL_READY:
        channels.append(f"อีเมล → {SMTP_TO}")
    if SMS_READY:
        channels.append(f"SMS → {SMS['to']}")
    return channels


def email_status() -> str:
    """ข้อความอธิบายสถานะอีเมลสำหรับหน้าแอดมิน"""
    if EMAIL_READY:
        return f"พร้อมส่งไปที่ {SMTP_TO}"
    if SMTP_TO and not SMTP_PASS:
        return f"ตั้งปลายทางไว้ที่ {SMTP_TO} แล้ว — รอใส่ App Password"
    return "ยังไม่ได้ตั้งค่า"


def sms_status() -> str:
    """ข้อความอธิบายสถานะ SMS สำหรับหน้าแอดมิน"""
    if SMS_READY:
        return f"พร้อมส่งไปที่ {SMS['to']} (ผ่าน {SMS['provider']})"
    if SMS["to"] and not SMS["key"]:
        return f"ตั้งปลายทางไว้ที่ {SMS['to']} แล้ว — รอใส่ API key"
    return "ยังไม่ได้ตั้งค่า"


def _post_json(url: str, payload: dict, headers: dict | None = None) -> None:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT):
        pass


def _send_webhook(text: str) -> None:
    # ส่งทั้ง content (Discord) และ text (Slack) เพื่อให้ใช้ได้ทั้งสองบริการ
    _post_json(WEBHOOK_URL, {"content": text, "text": text})


def _send_line(text: str) -> None:
    _post_json(
        "https://api.line.me/v2/bot/message/broadcast",
        {"messages": [{"type": "text", "text": text[:4900]}]},
        {"Authorization": f"Bearer {LINE_TOKEN}"},
    )


def _post_form(url: str, fields: dict, user: str, password: str) -> None:
    """POST แบบ form-encoded พร้อม HTTP Basic auth (ใช้กับผู้ให้บริการ SMS)"""
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(fields).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT):
        pass


def _e164_th(phone: str) -> str:
    """แปลงเบอร์ไทยเป็นรูปแบบสากล: 0849948889 -> +66849948889"""
    d = "".join(c for c in phone if c.isdigit())
    if d.startswith("66"):
        return "+" + d
    return "+66" + d[1:] if d.startswith("0") else "+" + d


def _send_sms(text: str) -> None:
    """ส่ง SMS — ข้อความไทยคิด 70 ตัวอักษรต่อข้อความ จึงส่งเฉพาะใจความสั้นๆ"""
    body = text[:300]
    if SMS["provider"] == "twilio":
        fields = {"To": _e164_th(SMS["to"]), "Body": body}
        if SMS["sender"]:
            fields["From"] = SMS["sender"]
        _post_form(
            f"https://api.twilio.com/2010-04-01/Accounts/{SMS['key']}/Messages.json",
            fields, SMS["key"], SMS["secret"],
        )
        return

    # ค่าเริ่มต้น: ThaiBulkSMS (API v2)
    fields = {"msisdn": SMS["to"], "message": body}
    if SMS["sender"]:
        fields["sender"] = SMS["sender"]
    _post_form("https://api-v2.thaibulksms.com/sms",
               fields, SMS["key"], SMS["secret"])


def _send_email(subject: str, text: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = SMTP_TO
    msg.set_content(text)

    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=TIMEOUT,
                              context=ssl.create_default_context()) as srv:
            if SMTP_USER:
                srv.login(SMTP_USER, SMTP_PASS)
            srv.send_message(msg)
        return

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=TIMEOUT) as srv:
        srv.starttls(context=ssl.create_default_context())
        if SMTP_USER:
            srv.login(SMTP_USER, SMTP_PASS)
        srv.send_message(msg)


def _deliver(subject: str, text: str, sms_text: str) -> None:
    """ส่งทุกช่องทางที่เปิดไว้ — ช่องหนึ่งพังต้องไม่ทำให้ช่องอื่นไม่ถูกส่ง"""
    jobs = []
    if WEBHOOK_URL:
        jobs.append(("webhook", lambda: _send_webhook(text)))
    if LINE_TOKEN:
        jobs.append(("line", lambda: _send_line(text)))
    if EMAIL_READY:
        jobs.append(("email", lambda: _send_email(subject, text)))
    if SMS_READY:
        jobs.append(("sms", lambda: _send_sms(sms_text)))

    for name, fn in jobs:
        try:
            fn()
        except (urllib.error.URLError, OSError, smtplib.SMTPException, ValueError) as exc:
            # แจ้งเตือนล้มเหลวไม่ใช่เรื่องคอขาดบาดตาย — บันทึกไว้ในล็อกพอ
            print(f"[notify] ส่งผ่าน {name} ไม่สำเร็จ: {exc}", flush=True)


def send_test() -> tuple[bool, str]:
    """ส่งข้อความทดสอบแบบ 'รอผล' เพื่อให้หน้าแอดมินรายงานได้ว่าสำเร็จหรือไม่

    ต่างจาก send() ตรงที่ไม่ยิงแล้วปล่อย — รอจนรู้ผลจริงแล้วคืนข้อความอธิบาย
    """
    channels = enabled_channels()
    if not channels:
        return False, "ยังไม่ได้เปิดช่องทางแจ้งเตือนใดเลย"

    subject = "🔔 ทดสอบการแจ้งเตือน — Khunakorn Sport"
    text = subject + "\n" + "\n".join([
        "ถ้าคุณได้รับข้อความนี้ แปลว่าตั้งค่าถูกต้องแล้ว",
        f"ระบบจะแจ้งเตือนเมื่อมีคำสั่งซื้อใหม่และมีการแจ้งชำระเงิน",
        f"ดูในระบบ: {SITE_URL}/admin/orders",
    ])
    sms_text = "ทดสอบแจ้งเตือน Khunakorn Sport ตั้งค่าถูกต้องแล้ว"

    jobs = []
    if WEBHOOK_URL:
        jobs.append(("Webhook", lambda: _send_webhook(text)))
    if LINE_TOKEN:
        jobs.append(("LINE", lambda: _send_line(text)))
    if EMAIL_READY:
        jobs.append(("อีเมล", lambda: _send_email(subject, text)))
    if SMS_READY:
        jobs.append(("SMS", lambda: _send_sms(sms_text)))

    ok, failed = [], []
    for name, fn in jobs:
        try:
            fn()
            ok.append(name)
        except Exception as exc:                      # noqa: BLE001 — รายงานทุกความผิดพลาด
            failed.append(f"{name} ({type(exc).__name__}: {exc})")

    if failed and ok:
        return False, f"ส่งสำเร็จ: {', '.join(ok)} · ล้มเหลว: {' · '.join(failed)}"
    if failed:
        return False, f"ส่งไม่สำเร็จ: {' · '.join(failed)}"
    return True, f"ส่งข้อความทดสอบเรียบร้อย: {', '.join(ok)}"


def send(subject: str, lines: list[str], sms: str | None = None) -> None:
    """ส่งแจ้งเตือนแบบไม่รอผล (ยิงแล้วปล่อย)

    sms = ข้อความสั้นสำหรับ SMS โดยเฉพาะ (คิดเงินตามความยาว)
    ถ้าไม่ระบุจะใช้หัวข้อแทน
    """
    if not enabled_channels():
        return
    text = subject + "\n" + "\n".join(lines)
    threading.Thread(
        target=_deliver, args=(subject, text, sms or subject), daemon=True
    ).start()


# ── ข้อความสำเร็จรูป ──────────────────────────────────────
def new_order(order: dict) -> None:
    items = "\n".join(
        f"  · {i['name']} ไซซ์ {i['size']} × {i['qty']}" for i in order["items"]
    )
    send(f"🛒 คำสั่งซื้อใหม่ {order['order_no']}", [
        f"ยอดรวม: ฿{order['total']:,}",
        f"ผู้รับ: {order['customer']['name']} ({order['customer']['phone']})",
        f"ที่อยู่: {order['customer']['address']}",
        "รายการ:",
        items,
        f"ดูในระบบ: {SITE_URL}/admin/orders",
    ], sms=f"ออเดอร์ใหม่ {order['order_no']} ยอด {order['total']:,} บาท "
           f"โทร {order['customer']['phone']}")


def new_payment(payment: dict, order: dict | None) -> None:
    matched = (
        f"ผูกกับคำสั่งซื้อ {order['order_no']} (ยอด ฿{order['total']:,})"
        if order else
        f"⚠️ ไม่พบคำสั่งซื้อ '{payment['order_id'] or '-'}' — ต้องตรวจสอบเอง"
    )
    sms = (f"แจ้งโอน {order['order_no']} ยอด {payment['amount'] or '-'} บาท รอตรวจสลิป"
           if order else
           f"แจ้งโอน {payment['amount'] or '-'} บาท ไม่พบเลขคำสั่งซื้อ ต้องตรวจเอง")
    send("💸 มีการแจ้งชำระเงินใหม่", [
        matched,
        f"ยอดที่แจ้ง: {payment['amount'] or '-'} บาท",
        f"ช่องทาง: {payment['method']}",
        f"สลิป: {'แนบมาแล้ว' if payment['slip'] else 'ไม่ได้แนบ'}",
        f"ตรวจสลิป: {SITE_URL}/admin/orders?tab=payments",
    ], sms=sms)

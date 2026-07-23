"""Multi-factor alert trigger logic, cooldown, and per-channel dispatch.

The *trigger* logic (``evaluate_alert``) is pure and unit-testable. The
*dispatch* logic (email / SMS / Telegram) is ported from the earlier Streamlit
project's ``src/alerts/*`` modules and keeps its "fail soft per channel"
behavior: a misconfigured or failing channel logs and returns an error string
instead of raising, so one bad channel never blocks the others.
"""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText

import config


# ---------------------------------------------------------------------------
# Pure trigger logic
# ---------------------------------------------------------------------------

def evaluate_alert(
    *,
    volume_z: float,
    imbalance: float,
    z_threshold: float,
    require_news: bool,
    news_direction: str | None,
) -> dict:
    """Decide whether conditions for a multi-factor alert are met.

    An alert requires BOTH a volume anomaly AND an order-flow shift (and, if
    ``require_news`` is on, a news confirmation in the same direction). Returns
    a dict with ``conditions_met``, the inferred ``direction``, and per-factor
    ``factors`` chips (label / met / detail), matching the JSX AlertCenter.
    """
    big_volume = volume_z >= z_threshold
    order_flow_shift = abs(imbalance) >= config.ORDERFLOW_SHIFT_THRESHOLD
    direction = "long" if imbalance > 0 else "short"
    news_confirms = (not require_news) or (news_direction == direction)
    conditions_met = big_volume and order_flow_shift and news_confirms

    factors = [
        {"label": "Volume anomaly", "met": bool(big_volume), "detail": f"z={volume_z:.2f}"},
        {"label": "Order-flow shift", "met": bool(order_flow_shift), "detail": f"imbalance={imbalance:.2f}"},
        {
            "label": "News confirmation",
            "met": (bool(news_confirms) if require_news else None),
            "detail": news_direction or "n/a",
        },
    ]
    return {"conditions_met": conditions_met, "direction": direction, "factors": factors}


# ---------------------------------------------------------------------------
# Channel dispatch (fail soft per channel)
# ---------------------------------------------------------------------------

def send_email(subject: str, body: str) -> dict:
    if not config.channel_availability()["email"]:
        return {"channel": "email", "ok": False, "error": "SMTP env vars not configured"}
    try:
        host = os.environ["SMTP_HOST"]
        port = int(os.environ.get("SMTP_PORT", "587"))
        user = os.environ["SMTP_USER"]
        password = os.environ["SMTP_PASSWORD"]
        sender = os.environ.get("ALERT_EMAIL_FROM", user)
        recipient = os.environ["ALERT_EMAIL_TO"]

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient

        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(sender, [recipient], msg.as_string())
        return {"channel": "email", "ok": True}
    except Exception as exc:  # fail soft
        return {"channel": "email", "ok": False, "error": str(exc)}


def send_sms(body: str) -> dict:
    if not config.channel_availability()["sms"]:
        return {"channel": "sms", "ok": False, "error": "Twilio env vars not configured"}
    try:
        from twilio.rest import Client  # imported lazily; optional dependency

        client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
        client.messages.create(
            body=body,
            from_=os.environ["TWILIO_FROM"],
            to=os.environ["TWILIO_TO"],
        )
        return {"channel": "sms", "ok": True}
    except Exception as exc:  # fail soft
        return {"channel": "sms", "ok": False, "error": str(exc)}


def send_telegram(body: str) -> dict:
    if not config.channel_availability()["telegram"]:
        return {"channel": "telegram", "ok": False, "error": "Telegram env vars not configured"}
    try:
        import requests

        token = os.environ["TELEGRAM_BOT_TOKEN"]
        chat_id = os.environ["TELEGRAM_CHAT_ID"]
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": body},
            timeout=15,
        )
        resp.raise_for_status()
        return {"channel": "telegram", "ok": True}
    except Exception as exc:  # fail soft
        return {"channel": "telegram", "ok": False, "error": str(exc)}


def dispatch_alert(subject: str, body: str, channels: list[str] | None = None) -> list[dict]:
    """Send to each requested (and available) channel, collecting per-channel results."""
    channels = channels or ["email", "sms", "telegram"]
    results: list[dict] = []
    if "email" in channels:
        results.append(send_email(subject, body))
    if "sms" in channels:
        results.append(send_sms(body))
    if "telegram" in channels:
        results.append(send_telegram(body))
    return results

"""Server-side notification dispatch for the bot client.

The bot client posts events to /bot/notify and this module reads SMTP and
TextBelt credentials from `system_configs` and sends them. Credentials
never leave the backend.
"""
import logging
from email.message import EmailMessage

import aiosmtplib
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import decrypt
from app.models.system_config import SystemConfig

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """Raised when a notification cannot be sent (config missing or transport failed)."""


async def _load_system_config(session: AsyncSession) -> SystemConfig | None:
    result = await session.execute(select(SystemConfig))
    return result.scalar_one_or_none()


async def send_email(
    to: str,
    subject: str,
    body: str,
    session: AsyncSession,
) -> None:
    config = await _load_system_config(session)
    if config is None or not config.smtp_server or not config.smtp_user:
        raise NotificationError("SMTP not configured")
    password = decrypt(config.smtp_password_enc) if config.smtp_password_enc else None
    if not password:
        raise NotificationError("SMTP password not configured")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.smtp_user
    msg["To"] = to
    msg.set_content(body)

    try:
        await aiosmtplib.send(
            msg,
            hostname=config.smtp_server,
            port=config.smtp_port or 587,
            username=config.smtp_user,
            password=password,
            start_tls=True,
            timeout=15,
        )
    except Exception as e:
        raise NotificationError(f"SMTP send failed: {e}") from e


async def send_sms(to: str, body: str, session: AsyncSession) -> None:
    config = await _load_system_config(session)
    if config is None or not config.textbelt_key_enc:
        raise NotificationError("TextBelt key not configured")
    api_key = decrypt(config.textbelt_key_enc)
    if not api_key:
        raise NotificationError("TextBelt key not configured")

    # TextBelt caps messages at ~160 chars; trim to avoid silent truncation.
    if len(body) > 160:
        body = body[:157] + "..."

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://textbelt.com/text",
                data={"phone": to, "message": body, "key": api_key},
            )
        result = resp.json()
    except Exception as e:
        raise NotificationError(f"TextBelt request failed: {e}") from e

    if not result.get("success"):
        raise NotificationError(f"TextBelt rejected send: {result.get('error') or result}")

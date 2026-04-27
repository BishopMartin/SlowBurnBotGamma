"""Server-side notification dispatch for the bot client.

The bot client posts events to /bot/notify and this module reads Resend and
TextBelt credentials from `system_configs` and sends them. Credentials
never leave the backend.
"""
import logging

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
    if config is None or not config.resend_api_key_enc or not config.resend_from_address:
        raise NotificationError("Resend not configured")
    api_key = decrypt(config.resend_api_key_enc)

    try:
        payload: dict = {
            "from": config.resend_from_address,
            "to": [to],
            "subject": subject or "SlowBurnBot",
            "text": body,
        }
        if config.resend_reply_to:
            payload["reply_to"] = config.resend_reply_to
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
        if resp.status_code not in (200, 201):
            logger.error("Resend rejected send: %s %s", resp.status_code, resp.text)
            raise NotificationError(f"Resend rejected send: {resp.status_code}")
    except NotificationError:
        raise
    except Exception as e:
        logger.error("Resend request failed: %s", e)
        raise NotificationError(f"Resend request failed: {e}") from e


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

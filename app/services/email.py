"""Email sending via Resend API using credentials stored in system_config."""
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import decrypt
from app.models.system_config import SystemConfig

logger = logging.getLogger(__name__)


async def _get_resend_config(session: AsyncSession) -> dict | None:
    result = await session.execute(select(SystemConfig))
    config = result.scalar_one_or_none()
    if config is None or not config.resend_api_key_enc or not config.resend_from_address:
        return None
    return {
        "api_key": decrypt(config.resend_api_key_enc),
        "from_address": config.resend_from_address,
        "reply_to": config.resend_reply_to,
    }


async def send_invite_email(
    to_email: str,
    invite_code: str,
    free_trial_days: int | None,
    session: AsyncSession,
) -> None:
    resend = await _get_resend_config(session)
    if resend is None:
        raise RuntimeError("Resend not configured. Set credentials in admin config first.")

    trial_line = ""
    if free_trial_days:
        trial_line = f"\nThis invite includes {free_trial_days} days of free Crawl-level access.\n"

    body = (
        f"You've been invited to join SlowBurnBot!\n"
        f"\nYour registration code: {invite_code}\n"
        f"{trial_line}"
        f"\nUse this code when creating your account.\n"
    )

    payload: dict = {
        "from": resend["from_address"],
        "to": [to_email],
        "subject": "SlowBurnBot — Invitation",
        "text": body,
    }
    if resend.get("reply_to"):
        payload["reply_to"] = resend["reply_to"]
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend['api_key']}"},
            json=payload,
        )

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Resend rejected invite email: {resp.status_code} {resp.text}")

    logger.info("Invite email sent to %s", to_email)

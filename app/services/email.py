"""Email sending via SMTP credentials stored in system_config."""
import logging
from email.message import EmailMessage

import aiosmtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import decrypt
from app.models.system_config import SystemConfig

logger = logging.getLogger(__name__)


async def _get_smtp_config(session: AsyncSession) -> dict | None:
    result = await session.execute(select(SystemConfig))
    config = result.scalar_one_or_none()
    if config is None or not config.smtp_server or not config.smtp_user:
        return None
    return {
        "server": config.smtp_server,
        "port": config.smtp_port or 587,
        "user": config.smtp_user,
        "password": decrypt(config.smtp_password_enc) if config.smtp_password_enc else None,
    }


async def send_invite_email(
    to_email: str,
    invite_code: str,
    free_trial_days: int | None,
    session: AsyncSession,
) -> None:
    smtp = await _get_smtp_config(session)
    if smtp is None:
        raise RuntimeError("SMTP not configured. Set credentials in admin config first.")

    trial_line = ""
    if free_trial_days:
        trial_line = f"\nThis invite includes {free_trial_days} days of free Crawl-level access.\n"

    body = (
        f"You've been invited to join SlowBurnBot!\n"
        f"\nYour registration code: {invite_code}\n"
        f"{trial_line}"
        f"\nUse this code when creating your account.\n"
    )

    msg = EmailMessage()
    msg["Subject"] = "SlowBurnBot — Invitation"
    msg["From"] = smtp["user"]
    msg["To"] = to_email
    msg.set_content(body)

    await aiosmtplib.send(
        msg,
        hostname=smtp["server"],
        port=smtp["port"],
        username=smtp["user"],
        password=smtp["password"],
        start_tls=True,
    )
    logger.info("Invite email sent to %s", to_email)

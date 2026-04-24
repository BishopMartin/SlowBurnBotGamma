"""Enforce account limits based on subscription tier."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.user import User
from app.plan_tiers import get_max_accounts


async def enforce_account_limits(user_id: uuid.UUID, session: AsyncSession) -> None:
    """System-disable or re-enable accounts based on the user's plan tier.

    Accounts within the limit (ordered by created_at ASC, oldest first) are
    re-enabled.  Accounts beyond the limit (newest first) are system-disabled.
    """
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        return

    max_accounts = get_max_accounts(user.plan_tier)

    result = await session.execute(
        select(Account)
        .where(Account.user_id == user_id)
        .order_by(Account.created_at.asc())
    )
    accounts = list(result.scalars().all())

    for idx, account in enumerate(accounts):
        should_disable = idx >= max_accounts
        if account.system_disabled != should_disable:
            account.system_disabled = should_disable

    await session.flush()

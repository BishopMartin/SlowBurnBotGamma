"""Shared FastAPI dependencies."""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_async_session
from app.models.subscription import Subscription
from app.models.user import User


def is_subscription_entitled(subscription: Subscription | None) -> bool:
    if subscription is None:
        return False
    if subscription.status == "active":
        return True
    if subscription.status == "trialing":
        end = subscription.current_period_end
        return end is not None and end > datetime.now(timezone.utc)
    return False


async def get_active_subscription(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> Subscription | None:
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    return result.scalar_one_or_none()


async def require_active_subscription(
    subscription: Subscription | None = Depends(get_active_subscription),
) -> Subscription:
    if not is_subscription_entitled(subscription):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required.",
        )
    return subscription

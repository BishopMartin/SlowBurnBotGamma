"""Shared FastAPI dependencies."""
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_async_session
from app.models.subscription import Subscription
from app.models.user import User


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
    if subscription is None or subscription.status != "active":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required.",
        )
    return subscription

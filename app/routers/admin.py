"""Admin-only endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_superuser
from app.database import get_async_session
from app.models.subscription import Subscription
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[dict])
async def list_users(
    _: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(User))
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
            "plan_tier": u.plan_tier,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.post("/users/{user_id}/sync-subscription")
async def sync_subscription(
    user_id: uuid.UUID,
    _: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    """Manually re-sync a user's subscription status from Stripe."""
    import stripe as stripe_lib
    from app.settings import settings

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured.")

    stripe_lib.api_key = settings.stripe_secret_key

    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None or not sub.stripe_subscription_id:
        raise HTTPException(status_code=404, detail="No Stripe subscription on record.")

    stripe_sub = stripe_lib.Subscription.retrieve(sub.stripe_subscription_id)
    sub.status = stripe_sub.status
    sub.current_period_end = stripe_sub.current_period_end
    await session.commit()
    return {"status": sub.status}

"""Admin-only endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_superuser
from app.database import get_async_session
from app.models.account import Account
from app.models.follow_target import FollowTarget
from app.models.subscription import Subscription
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[dict])
async def list_users(
    _: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(User).options(selectinload(User.subscription))
    )
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
            "plan_tier": u.plan_tier,
            "is_active": u.is_active,
            "subscription_status": u.subscription.status if u.subscription else "none",
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


@router.post("/users/{user_id}/activate")
async def activate_subscription(
    user_id: uuid.UUID,
    _: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    """Admin-activate a user's subscription (set status=active, plan_tier=pro)."""
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="No subscription record found.")
    sub.status = "active"
    sub.plan_tier = "pro"

    # Also update the user's plan_tier field to stay in sync
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.plan_tier = "pro"

    await session.commit()
    return {"status": sub.status, "plan_tier": sub.plan_tier}


@router.post("/users/{user_id}/deactivate")
async def deactivate_subscription(
    user_id: uuid.UUID,
    _: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    """Admin-deactivate a user's subscription."""
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="No subscription record found.")
    sub.status = "inactive"
    sub.plan_tier = "free"

    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.plan_tier = "free"

    await session.commit()
    return {"status": sub.status, "plan_tier": sub.plan_tier}


@router.get("/accounts", response_model=list[dict])
async def list_all_accounts(
    _: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Account, User.email)
        .join(User, Account.user_id == User.id)
        .order_by(User.email, Account.name)
    )
    rows = result.all()
    return [
        {
            "id": str(a.id),
            "user_id": str(a.user_id),
            "user_email": email,
            "name": a.name,
            "enabled": a.enabled,
            "group_number": a.group_number,
            "created_at": a.created_at.isoformat(),
        }
        for a, email in rows
    ]


@router.get("/accounts/{account_id}/follow-targets", response_model=dict)
async def list_follow_targets(
    account_id: uuid.UUID,
    _: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
):
    offset = (page - 1) * page_size

    total_result = await session.execute(
        select(func.count()).where(FollowTarget.account_id == account_id)
    )
    total = total_result.scalar_one()

    result = await session.execute(
        select(FollowTarget)
        .where(FollowTarget.account_id == account_id)
        .order_by(FollowTarget.follow_date.desc().nullslast(), FollowTarget.target_handle)
        .offset(offset)
        .limit(page_size)
    )
    targets = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(t.id),
                "target_handle": t.target_handle,
                "source": t.source,
                "status": t.status,
                "follow_date": t.follow_date.isoformat() if t.follow_date else None,
                "unfollow_date": t.unfollow_date.isoformat() if t.unfollow_date else None,
                "follow_back": t.follow_back,
            }
            for t in targets
        ],
    }

"""Customer-facing subscription info."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_async_session
from app.deps import get_active_subscription
from app.models.account import Account
from app.models.subscription import Subscription
from app.models.user import User
from app.plan_tiers import PLAN_TIERS, get_max_accounts

router = APIRouter(prefix="/subscription", tags=["subscription"])


class TierInfo(BaseModel):
    name: str
    price: int
    max_accounts: int


class SubscriptionInfoRead(BaseModel):
    plan_tier: str
    status: str
    max_accounts: int
    current_accounts: int
    current_period_end: str | None = None
    tiers: list[TierInfo]


@router.get("/me", response_model=SubscriptionInfoRead)
async def get_subscription_info(
    user: User = Depends(current_active_user),
    subscription: Subscription | None = Depends(get_active_subscription),
    session: AsyncSession = Depends(get_async_session),
):
    plan_tier = subscription.plan_tier if subscription else "free"
    sub_status = subscription.status if subscription else "inactive"
    period_end = (
        subscription.current_period_end.isoformat()
        if subscription and subscription.current_period_end
        else None
    )

    count_result = await session.execute(
        select(func.count()).where(Account.user_id == user.id)
    )
    current_accounts = count_result.scalar_one()

    tiers = [
        TierInfo(name=name, price=info["price"], max_accounts=info["max_accounts"])
        for name, info in PLAN_TIERS.items()
    ]

    return SubscriptionInfoRead(
        plan_tier=plan_tier,
        status=sub_status,
        max_accounts=get_max_accounts(plan_tier),
        current_accounts=current_accounts,
        current_period_end=period_end,
        tiers=tiers,
    )

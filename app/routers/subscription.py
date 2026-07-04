"""Customer-facing subscription info."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_async_session
from app.deps import get_active_subscription
from app.models.account import Account
from app.models.desktop_build import DesktopBuild
from app.models.subscription import Subscription
from app.models.user import User
from app.plan_tiers import PLAN_TIERS, get_max_accounts, get_max_clients

router = APIRouter(prefix="/subscription", tags=["subscription"])


class TierInfo(BaseModel):
    name: str
    price: int
    max_accounts: int
    max_clients: int


class SubscriptionInfoRead(BaseModel):
    plan_tier: str
    status: str
    max_accounts: int
    current_accounts: int
    max_clients: int
    current_clients: int
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

    current_accounts = await session.scalar(
        select(func.count()).where(Account.user_id == user.id)
    )

    current_clients = await session.scalar(
        select(func.count()).where(
            DesktopBuild.user_id == user.id,
            DesktopBuild.status.notin_(DesktopBuild.NON_OCCUPYING_STATUSES),
        )
    )

    tiers = [
        TierInfo(
            name=name,
            price=info["price"],
            max_accounts=info["max_accounts"],
            max_clients=info["max_clients"],
        )
        for name, info in PLAN_TIERS.items()
    ]

    return SubscriptionInfoRead(
        plan_tier=plan_tier,
        status=sub_status,
        max_accounts=get_max_accounts(plan_tier),
        current_accounts=current_accounts,
        max_clients=get_max_clients(plan_tier),
        current_clients=current_clients,
        current_period_end=period_end,
        tiers=tiers,
    )

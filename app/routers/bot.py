"""Exe-facing endpoints — called by the compiled SlowBurnBot client."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_async_session
from app.deps import get_active_subscription, require_active_subscription
from app.models.account import Account
from app.models.account_settings import AccountSettings
from app.models.activity_log import ActivityLog
from app.models.session_log import SessionLog
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.bot import ActivityLogCreate, EntitlementRead, SessionLogCreate

router = APIRouter(prefix="/bot", tags=["bot"])


async def _assert_account_owned(
    account_id: uuid.UUID, user: User, session: AsyncSession
) -> Account:
    result = await session.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    return account


@router.get("/entitlement", response_model=EntitlementRead)
async def check_entitlement(
    subscription: Subscription | None = Depends(get_active_subscription),
):
    """Startup entitlement check for the exe."""
    if subscription is None:
        return EntitlementRead(active=False, plan_tier="free")
    return EntitlementRead(
        active=subscription.status == "active",
        plan_tier=subscription.plan_tier,
        current_period_end=subscription.current_period_end,
    )


@router.get("/settings/{account_id}")
async def get_bot_settings(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """Fetch account settings for the exe — requires active subscription."""
    await _assert_account_owned(account_id, user, session)
    result = await session.execute(
        select(AccountSettings).where(AccountSettings.account_id == account_id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not configured.")
    return settings


@router.post("/session-log", status_code=status.HTTP_201_CREATED)
async def post_session_log(
    body: SessionLogCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Batch session summary from the exe at end of run."""
    await _assert_account_owned(body.account_id, user, session)
    log = SessionLog(**body.model_dump(), user_id=user.id)
    session.add(log)
    await session.commit()
    return {"id": str(log.id)}


@router.post("/activity-log", status_code=status.HTTP_201_CREATED)
async def post_activity_log(
    body: ActivityLogCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Fine-grained activity or error event from the exe."""
    await _assert_account_owned(body.account_id, user, session)
    log = ActivityLog(**body.model_dump(), user_id=user.id)
    session.add(log)
    await session.commit()
    return {"id": str(log.id)}

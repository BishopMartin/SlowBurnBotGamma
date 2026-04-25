"""Exe-facing endpoints — called by the compiled SlowBurnBot client."""
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.crypto import decrypt
from app.database import get_async_session
from app.deps import get_active_subscription, require_active_subscription
from app.models.account import Account
from app.models.account_settings import AccountSettings
from app.models.activity_log import ActivityLog
from app.models.follow_target import FollowTarget
from app.models.ignore_handle import IgnoreHandle
from app.models.client_heartbeat import ClientHeartbeat
from app.models.session_log import SessionLog
from app.models.subscription import Subscription
from app.models.user import User
from app.models.system_config import SystemConfig
from app.models.user_config import UserConfig
from app.schemas.bot import (
    ActivityLogCreate,
    BotUserConfigRead,
    CredentialsRead,
    EntitlementRead,
    FollowTargetCreate,
    FollowTargetRead,
    FollowTargetUpdate,
    HeartbeatCreate,
    IgnoreHandlesRead,
    NotificationCredentialsForBot,
    RunCountRead,
    SessionLogCreate,
)

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


@router.get("/config", response_model=BotUserConfigRead)
async def get_bot_config(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Fetch user-wide config (notification prefs) for the exe."""
    result = await session.execute(
        select(UserConfig).where(UserConfig.user_id == user.id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        config = UserConfig(user_id=user.id, notify_email=user.email)
        session.add(config)
        await session.commit()
        await session.refresh(config)
    return config


@router.get("/notification-credentials", response_model=NotificationCredentialsForBot)
async def get_bot_notification_credentials(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Return decrypted SMTP/TextBelt credentials for the exe."""
    result = await session.execute(select(SystemConfig))
    config = result.scalar_one_or_none()
    if config is None:
        return NotificationCredentialsForBot(smtp_server="", smtp_port=587)
    return NotificationCredentialsForBot(
        smtp_server=config.smtp_server or "",
        smtp_port=config.smtp_port or 587,
        smtp_user=config.smtp_user,
        smtp_password=decrypt(config.smtp_password_enc) if config.smtp_password_enc else None,
        textbelt_key=decrypt(config.textbelt_key_enc) if config.textbelt_key_enc else None,
    )


@router.get("/settings/{account_id}")
async def get_bot_settings(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """Fetch account settings for the exe — requires active subscription."""
    account = await _assert_account_owned(account_id, user, session)
    result = await session.execute(
        select(AccountSettings).where(AccountSettings.account_id == account_id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = AccountSettings(account_id=account_id, user_id=user.id)
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
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


@router.get("/credentials/{account_id}", response_model=CredentialsRead)
async def get_bot_credentials(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """Return decrypted IG password for the exe — requires active subscription."""
    account = await _assert_account_owned(account_id, user, session)
    ig_password = decrypt(account.ig_password_enc) if account.ig_password_enc else None
    return CredentialsRead(ig_password=ig_password)


@router.get("/ignore-handles", response_model=IgnoreHandlesRead)
async def get_ignore_handles(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Return all ignore handles for the user."""
    result = await session.execute(
        select(IgnoreHandle.handle).where(IgnoreHandle.user_id == user.id)
    )
    handles = [row[0] for row in result.all()]
    return IgnoreHandlesRead(handles=handles)


@router.get("/follow-targets/{account_id}", response_model=list[FollowTargetRead])
async def get_bot_follow_targets(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    status_filter: str | None = Query(None, alias="status"),
    older_than_days: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(500, ge=1, le=5000),
):
    """Return follow targets for an account with optional filtering."""
    await _assert_account_owned(account_id, user, session)
    query = select(FollowTarget).where(FollowTarget.account_id == account_id)
    if status_filter:
        query = query.where(FollowTarget.status == status_filter)
    if older_than_days is not None:
        cutoff = date.today() - timedelta(days=older_than_days)
        query = query.where(FollowTarget.follow_date <= cutoff)
    query = query.order_by(FollowTarget.follow_date.asc().nullslast())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    return [FollowTargetRead.model_validate(t, from_attributes=True) for t in result.scalars().all()]


@router.post("/follow-targets", status_code=status.HTTP_201_CREATED)
async def create_bot_follow_target(
    body: FollowTargetCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new follow target record from the exe."""
    await _assert_account_owned(body.account_id, user, session)
    target = FollowTarget(**body.model_dump(), user_id=user.id)
    session.add(target)
    await session.commit()
    return {"id": str(target.id)}


@router.patch("/follow-targets/{target_id}")
async def update_bot_follow_target(
    target_id: uuid.UUID,
    body: FollowTargetUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Update a follow target (status, unfollow_date, follow_back) from the exe."""
    result = await session.execute(
        select(FollowTarget).where(FollowTarget.id == target_id, FollowTarget.user_id == user.id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow target not found.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(target, field, value)
    await session.commit()
    return {"id": str(target.id)}


@router.get("/run-count/{account_id}", response_model=RunCountRead)
async def get_run_count(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    run_date: date | None = Query(None),
):
    """Count session logs for an account on a given date (defaults to today)."""
    await _assert_account_owned(account_id, user, session)
    target_date = run_date or date.today()
    count = await session.scalar(
        select(func.count()).where(
            SessionLog.account_id == account_id,
            SessionLog.run_date == target_date,
        )
    )
    return RunCountRead(count=count or 0)


@router.post("/heartbeat")
async def post_heartbeat(
    body: HeartbeatCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Upsert client heartbeat — called every ~60s by the bot client."""
    result = await session.execute(
        select(ClientHeartbeat).where(
            ClientHeartbeat.user_id == user.id,
            ClientHeartbeat.client_id == body.client_id,
        )
    )
    hb = result.scalar_one_or_none()
    if hb is None:
        hb = ClientHeartbeat(user_id=user.id, client_id=body.client_id)
        session.add(hb)
    hb.system_type = body.system_type
    hb.ip_address = body.ip_address
    hb.status = body.status
    hb.current_account = body.current_account
    from datetime import datetime, timezone
    hb.last_heartbeat = datetime.now(timezone.utc)
    await session.commit()
    return {"ok": True}

"""Account CRUD — dashboard use."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_async_session
from app.models.account import Account
from app.models.account_settings import AccountSettings
from app.models.follow_target import FollowTarget
from app.models.user import User
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.schemas.account_settings import AccountSettingsRead, AccountSettingsUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


async def _get_owned_account(
    account_id: uuid.UUID,
    user: User,
    session: AsyncSession,
) -> Account:
    result = await session.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    return account


@router.get("", response_model=list[AccountRead])
async def list_accounts(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Account).where(Account.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: AccountCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    account = Account(**body.model_dump(), user_id=user.id)
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountRead)
async def get_account(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await _get_owned_account(account_id, user, session)


@router.patch("/{account_id}", response_model=AccountRead)
async def update_account(
    account_id: uuid.UUID,
    body: AccountUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    account = await _get_owned_account(account_id, user, session)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    await session.commit()
    await session.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    account = await _get_owned_account(account_id, user, session)
    await session.delete(account)
    await session.commit()


@router.get("/{account_id}/settings", response_model=AccountSettingsRead)
async def get_account_settings(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    await _get_owned_account(account_id, user, session)
    result = await session.execute(
        select(AccountSettings).where(AccountSettings.account_id == account_id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found.")
    return settings


@router.put("/{account_id}/settings", response_model=AccountSettingsRead)
async def upsert_account_settings(
    account_id: uuid.UUID,
    body: AccountSettingsUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    await _get_owned_account(account_id, user, session)
    result = await session.execute(
        select(AccountSettings).where(AccountSettings.account_id == account_id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = AccountSettings(account_id=account_id, user_id=user.id)
        session.add(settings)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)

    await session.commit()
    await session.refresh(settings)
    return settings


@router.get("/{account_id}/database", response_model=dict)
async def get_account_database(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
):
    await _get_owned_account(account_id, user, session)
    offset = (page - 1) * page_size

    total = await session.scalar(
        select(func.count()).where(FollowTarget.account_id == account_id)
    )
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

"""User-wide configuration endpoints."""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_async_session
from app.models.ignore_handle import IgnoreHandle
from app.models.user import User
from app.models.user_config import UserConfig
from app.schemas.user_config import UserConfigRead, UserConfigUpdate

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=UserConfigRead)
async def get_config(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
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


@router.put("", response_model=UserConfigRead)
async def update_config(
    body: UserConfigUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(UserConfig).where(UserConfig.user_id == user.id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        config = UserConfig(user_id=user.id, notify_email=user.email)
        session.add(config)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(config, field, value)

    await session.commit()
    await session.refresh(config)
    return config


class IgnoreHandlesUpdate(BaseModel):
    handles: list[str]


@router.get("/ignore-handles", response_model=IgnoreHandlesUpdate)
async def get_ignore_handles(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(IgnoreHandle.handle).where(IgnoreHandle.user_id == user.id)
    )
    return IgnoreHandlesUpdate(handles=[row[0] for row in result.all()])


@router.put("/ignore-handles", response_model=IgnoreHandlesUpdate)
async def update_ignore_handles(
    body: IgnoreHandlesUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    await session.execute(
        delete(IgnoreHandle).where(IgnoreHandle.user_id == user.id)
    )
    clean = [h.strip().lower() for h in body.handles if h.strip()]
    seen: set[str] = set()
    for handle in clean:
        if handle not in seen:
            seen.add(handle)
            session.add(IgnoreHandle(id=uuid.uuid4(), user_id=user.id, handle=handle))
    await session.commit()
    return IgnoreHandlesUpdate(handles=sorted(seen))

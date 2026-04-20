"""User-wide configuration endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_async_session
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
        config = UserConfig(user_id=user.id)
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
        config = UserConfig(user_id=user.id)
        session.add(config)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(config, field, value)

    await session.commit()
    await session.refresh(config)
    return config

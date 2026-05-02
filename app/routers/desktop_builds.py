"""Desktop build endpoints — dashboard-facing."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_async_session
from app.deps import require_active_subscription
from app.models.desktop_build import DesktopBuild
from app.models.subscription import Subscription
from app.models.system_config import SystemConfig
from app.models.user import User
from app.plan_tiers import get_max_clients
from app.schemas.desktop_build import (
    DesktopBuildCreate,
    DesktopBuildRead,
    DesktopBuildWithToken,
)
from app.services.object_storage import generate_signed_get_url
from app.settings import settings

router = APIRouter(prefix="/desktop-builds", tags=["desktop-builds"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mint_token(user_id: uuid.UUID, client_id: int) -> tuple[str, str]:
    """Return (plaintext_token, sha256_hex_hash).

    Token format: {user_id}_{client_id}_{random_secret}
    The client can parse user_id and client_id from the token directly,
    eliminating the need to prompt for them separately on first run.
    """
    secret = secrets.token_urlsafe(32)
    token = f"{user_id}_{client_id}_{secret}"
    return token, hashlib.sha256(token.encode()).hexdigest()


def _system_type(build: DesktopBuild) -> str:
    return build.build_options.get("system_type", "windows")


async def _get_system_config(session: AsyncSession) -> SystemConfig:
    sc = await session.scalar(select(SystemConfig))
    if sc is None:
        sc = SystemConfig()
        session.add(sc)
        await session.commit()
        await session.refresh(sc)
    return sc


async def _get_owned_build(
    build_id: uuid.UUID,
    user: User,
    session: AsyncSession,
) -> DesktopBuild:
    build = await session.scalar(
        select(DesktopBuild).where(
            DesktopBuild.id == build_id,
            DesktopBuild.user_id == user.id,
        )
    )
    if build is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found.")
    return build


@router.get("/meta")
async def get_desktop_builds_meta(
    _: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Return current bot version from DB."""
    sc = await _get_system_config(session)
    return {
        "current_bot_version": sc.current_bot_version or "",
        "current_bot_release_date": sc.current_bot_release_date or "",
    }


@router.post("", response_model=DesktopBuildWithToken, status_code=status.HTTP_201_CREATED)
async def create_desktop_build(
    body: DesktopBuildCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """Configure a new client slot and mint an activation token. No build is dispatched."""
    max_clients = get_max_clients(user.plan_tier)
    current_clients = await session.scalar(
        select(func.count()).where(
            DesktopBuild.user_id == user.id,
            DesktopBuild.status.notin_(["revoked"]),
        )
    )
    if max_clients > 0 and current_clients >= max_clients:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Client limit reached for your plan ({max_clients} clients).",
        )

    if body.slot_number is not None:
        next_client_id = body.slot_number
    else:
        occupied = set(await session.scalars(
            select(DesktopBuild.client_id).where(
                DesktopBuild.user_id == user.id,
                DesktopBuild.status.notin_(["revoked"]),
            )
        ))
        next_client_id = 1
        while next_client_id in occupied:
            next_client_id += 1

    now = _now()
    token, token_hash = _mint_token(user.id, next_client_id)
    sc = await _get_system_config(session)

    build = DesktopBuild(
        user_id=user.id,
        client_id=next_client_id,
        build_options=body.config.model_dump(),
        status="pending_activation",
        bot_version=sc.current_bot_version or None,
        activation_token_hash=token_hash,
        activation_token_expires_at=now + timedelta(hours=settings.desktop_activation_token_ttl_hours),
    )
    session.add(build)
    await session.commit()
    await session.refresh(build)

    read = DesktopBuildRead.model_validate(build)
    return DesktopBuildWithToken(**read.model_dump(), activation_token=token)


@router.get("", response_model=list[DesktopBuildRead])
async def list_desktop_builds(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """List the current user's builds, newest first."""
    rows = await session.scalars(
        select(DesktopBuild)
        .where(DesktopBuild.user_id == user.id)
        .order_by(DesktopBuild.created_at.desc())
    )
    return [DesktopBuildRead.model_validate(b) for b in rows.all()]


@router.get("/{build_id}", response_model=DesktopBuildRead)
async def get_desktop_build(
    build_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """Return a single build's current status."""
    build = await _get_owned_build(build_id, user, session)
    return DesktopBuildRead.model_validate(build)


@router.get("/{build_id}/download-url")
async def get_download_url(
    build_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """
    Windows: return a short-lived signed URL to the generic release binary in object storage.
    Linux: return docker run instructions with the activation token pre-filled.
    """
    build = await _get_owned_build(build_id, user, session)

    if _system_type(build) == "linux":
        bot_version = build.bot_version or "latest"
        image_ref = f"{settings.ghcr_namespace}/slowburnbot-client:{bot_version}"
        # Activation token not returned here — it's shown on the build row at creation time
        return {
            "image_ref": image_ref,
            "pull_cmd": f"docker pull {image_ref}",
            "run_cmd": (
                f"docker run -it --rm "
                f"-e USER_ID={user.id} "
                f"-e CLIENT_ID={build.client_id} "
                f"-e ACTIVATION_TOKEN=<paste-token-here> "
                f"-v ./slowburn-config:/app/config "
                f"{image_ref}"
            ),
        }

    if not settings.bucket_name or not settings.bucket_access_key_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage not configured.",
        )

    bot_version = build.bot_version or "latest"
    key = f"releases/windows/SlowBurnBot-{bot_version}.exe"
    signed_url = generate_signed_get_url(key, expires_seconds=settings.desktop_signed_url_expires_seconds)
    return {"url": signed_url, "filename": f"SlowBurnBot-client{build.client_id}.exe"}


@router.delete("/{build_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_desktop_build(
    build_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """User-initiated revoke — hard-deletes the build row, freeing the slot."""
    build = await _get_owned_build(build_id, user, session)
    await session.delete(build)
    await session.commit()


@router.post("/{build_id}/rebuild", response_model=DesktopBuildWithToken, status_code=status.HTTP_201_CREATED)
async def rebuild_desktop_build(
    build_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """Re-mint the activation token for an existing slot without changing its config."""
    build = await _get_owned_build(build_id, user, session)

    now = _now()
    token, token_hash = _mint_token(build.user_id, build.client_id)

    build.status = "pending_activation"
    build.activation_token_hash = token_hash
    build.activation_token_expires_at = now + timedelta(hours=settings.desktop_activation_token_ttl_hours)
    build.consumed_at = None
    build.activated_at = None
    await session.commit()
    await session.refresh(build)

    read = DesktopBuildRead.model_validate(build)
    return DesktopBuildWithToken(**read.model_dump(), activation_token=token)

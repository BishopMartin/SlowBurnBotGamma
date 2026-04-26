"""Desktop build endpoints — dashboard-facing."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_async_session
from app.deps import require_active_subscription
from app.models.desktop_build import DesktopBuild
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.desktop_build import (
    DesktopBuildCreate,
    DesktopBuildRead,
    DesktopBuildWithToken,
)
from app.services import github_actions
from app.settings import settings

router = APIRouter(prefix="/desktop-builds", tags=["desktop-builds"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mint_token() -> tuple[str, str]:
    """Return (plaintext_token, sha256_hex_hash)."""
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


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


async def _poll_github_status(build: DesktopBuild, session: AsyncSession) -> None:
    """Update build status by querying GitHub if still in-flight."""
    if build.status not in ("queued", "running"):
        return

    if build.github_run_id is None:
        run_id = await github_actions.find_run_for_build(
            str(build.id), build.created_at
        )
        if run_id:
            build.github_run_id = run_id
        else:
            return  # Run not yet visible on GitHub

    try:
        run = await github_actions.get_workflow_run(build.github_run_id)
    except Exception:
        return  # Leave status unchanged on transient error

    gh_status = run.get("status")
    gh_conclusion = run.get("conclusion")

    if gh_status == "completed":
        if gh_conclusion == "success":
            build.status = "ready"
            build.artifact_name = "SlowBurnBot.exe"
        else:
            build.status = "failed"
            build.failure_reason = gh_conclusion or "unknown"
    elif gh_status == "in_progress":
        build.status = "running"

    await session.commit()
    await session.refresh(build)


@router.post("", response_model=DesktopBuildWithToken, status_code=status.HTTP_201_CREATED)
async def create_desktop_build(
    body: DesktopBuildCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """Configure and request a new per-customer Windows EXE build."""
    # Resolve api_url: use client-supplied value or fall back to the server's PUBLIC_API_URL
    config = body.config
    api_url = (config.api_url or settings.public_api_url).rstrip("/")

    # Allocate next client_id for this user
    max_cid = await session.scalar(
        select(func.coalesce(func.max(DesktopBuild.client_id), 0)).where(
            DesktopBuild.user_id == user.id
        )
    )
    next_client_id = (max_cid or 0) + 1

    now = _now()
    token, token_hash = _mint_token()

    build = DesktopBuild(
        user_id=user.id,
        client_id=next_client_id,
        build_options=config.model_dump(),
        status="queued",
        activation_token_hash=token_hash,
        activation_token_expires_at=now
        + timedelta(hours=settings.desktop_activation_token_ttl_hours),
        download_expires_at=now + timedelta(hours=settings.desktop_download_expires_hours),
    )
    session.add(build)
    await session.commit()
    await session.refresh(build)

    # Dispatch GitHub Actions workflow (non-blocking failure rolls back to queued)
    try:
        await github_actions.dispatch_workflow(
            build_id=str(build.id),
            user_id=str(user.id),
            client_id=next_client_id,
            api_url=api_url,
            activation_token=token,
            build_options=config.model_dump(),
        )
    except Exception as exc:
        build.status = "failed"
        build.failure_reason = str(exc)[:500]
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
    """Poll a single build's status. Queries GitHub if still in-flight."""
    build = await _get_owned_build(build_id, user, session)
    if settings.github_token and settings.github_repo:
        await _poll_github_status(build, session)
    return DesktopBuildRead.model_validate(build)


@router.get("/{build_id}/download")
async def download_desktop_build(
    build_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """Stream the built EXE to the user via GitHub artifact proxy."""
    build = await _get_owned_build(build_id, user, session)

    if build.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Build is not ready (status: {build.status}).",
        )
    if _now() > build.download_expires_at:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Download link has expired.",
        )
    if not build.github_run_id or not build.artifact_name:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Artifact location not recorded.",
        )

    exe_bytes, sha256 = await github_actions.download_artifact(
        build.github_run_id, build.artifact_name
    )

    if not build.artifact_sha256:
        build.artifact_sha256 = sha256
        build.file_size_bytes = len(exe_bytes)
    await session.commit()

    return StreamingResponse(
        iter([exe_bytes]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="SlowBurnBot-client{build.client_id}.exe"',
            "Content-Length": str(len(exe_bytes)),
        },
    )


@router.post("/{build_id}/revoke", response_model=DesktopBuildRead)
async def revoke_desktop_build(
    build_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """User-initiated revoke — marks build as revoked."""
    build = await _get_owned_build(build_id, user, session)
    if build.status == "revoked":
        return DesktopBuildRead.model_validate(build)
    build.status = "revoked"
    await session.commit()
    await session.refresh(build)
    return DesktopBuildRead.model_validate(build)

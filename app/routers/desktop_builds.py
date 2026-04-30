"""Desktop build endpoints — dashboard-facing."""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user, current_active_user_optional
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
from app.services import github_actions
from app.settings import settings

router = APIRouter(prefix="/desktop-builds", tags=["desktop-builds"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mint_token() -> tuple[str, str]:
    """Return (plaintext_token, sha256_hex_hash)."""
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


_DL_TOKEN_TTL = 120  # seconds


async def _get_system_config(session: AsyncSession) -> SystemConfig:
    sc = await session.scalar(select(SystemConfig))
    if sc is None:
        sc = SystemConfig()
        session.add(sc)
        await session.commit()
        await session.refresh(sc)
    return sc


def _version_gt(a: str, b: str) -> bool:
    def parse(v): return [int(x) for x in v.split(".")]
    try:
        return parse(a) > parse(b)
    except Exception:
        return False


def _make_download_token(build_id: uuid.UUID, user_id: uuid.UUID) -> str:
    expires = int(_now().timestamp()) + _DL_TOKEN_TTL
    payload = f"{build_id}:{user_id}:{expires}"
    sig = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{expires}.{sig}"


def _verify_download_token(token: str, build_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    try:
        expires_str, sig = token.split(".", 1)
        expires = int(expires_str)
    except (ValueError, AttributeError):
        return False
    if int(_now().timestamp()) > expires:
        return False
    payload = f"{build_id}:{user_id}:{expires}"
    expected = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


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
            if not build.bot_version:
                head_sha = run.get("head_sha")
                if head_sha:
                    build.bot_version = await github_actions.get_bot_version_from_commit(head_sha)
            if build.bot_version:
                sc = await _get_system_config(session)
                if sc.current_bot_version is None or _version_gt(build.bot_version, sc.current_bot_version):
                    sc.current_bot_version = build.bot_version
                    sc.current_bot_release_date = _now().strftime("%b %d %Y")
        else:
            build.status = "failed"
            build.failure_reason = gh_conclusion or "unknown"
    elif gh_status == "in_progress":
        build.status = "running"

    await session.commit()
    await session.refresh(build)


@router.get("/meta")
async def get_desktop_builds_meta(
    _: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Return metadata about desktop builds — current bot version from DB."""
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
    """Configure and request a new per-customer Windows EXE build."""
    # Enforce per-plan client limit
    max_clients = get_max_clients(user.plan_tier)
    current_clients = await session.scalar(
        select(func.count()).where(
            DesktopBuild.user_id == user.id,
            DesktopBuild.status.notin_(["revoked", "failed"]),
        )
    )
    if max_clients > 0 and current_clients >= max_clients:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Client limit reached for your plan ({max_clients} clients).",
        )

    # Resolve api_url: use client-supplied value or fall back to the server's PUBLIC_API_URL
    config = body.config
    api_url = (config.api_url or settings.public_api_url).rstrip("/")

    # Assign client_id: use explicit slot_number (rebuild) or lowest free slot (new build)
    if body.slot_number is not None:
        next_client_id = body.slot_number
    else:
        occupied = set(await session.scalars(
            select(DesktopBuild.client_id).where(
                DesktopBuild.user_id == user.id,
                DesktopBuild.status.notin_(["revoked", "failed"]),
            )
        ))
        next_client_id = 1
        while next_client_id in occupied:
            next_client_id += 1

    now = _now()
    token, token_hash = _mint_token()
    sc = await _get_system_config(session)

    build = DesktopBuild(
        user_id=user.id,
        client_id=next_client_id,
        build_options=config.model_dump(),
        status="queued",
        bot_version=sc.current_bot_version or None,
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


@router.post("/{build_id}/download-token")
async def get_download_token(
    build_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """Return a short-lived signed token for browser-native download."""
    build = await _get_owned_build(build_id, user, session)
    if build.status != "ready":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Build not ready.")
    if _now() > build.download_expires_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Download expired.")
    return {"token": _make_download_token(build_id, user.id)}


@router.get("/{build_id}/download")
async def download_desktop_build(
    build_id: uuid.UUID,
    dt: str | None = Query(default=None),
    user: User | None = Depends(current_active_user_optional),
    session: AsyncSession = Depends(get_async_session),
):
    """Stream the built EXE to the user via GitHub artifact proxy."""
    # Auth: either Bearer token (user dep) or short-lived download token (?dt=)
    if dt:
        build = await session.scalar(
            select(DesktopBuild).where(DesktopBuild.id == build_id)
        )
        if not build or not _verify_download_token(dt, build_id, build.user_id):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired download token.")
    elif user:
        build = await _get_owned_build(build_id, user, session)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

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


@router.post("/{build_id}/rebuild", response_model=DesktopBuildWithToken, status_code=status.HTTP_201_CREATED)
async def rebuild_desktop_build(
    build_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
    _: Subscription = Depends(require_active_subscription),
):
    """Revoke an existing build and queue a new one with the same config."""
    old_build = await _get_owned_build(build_id, user, session)

    # Revoke the old build (frees up a slot for the new one)
    old_build.status = "revoked"
    await session.commit()

    config_dict = old_build.build_options
    api_url = (config_dict.get("api_url") or settings.public_api_url).rstrip("/")
    next_client_id = old_build.client_id

    now = _now()
    token, token_hash = _mint_token()
    sc = await _get_system_config(session)

    new_build = DesktopBuild(
        user_id=user.id,
        client_id=next_client_id,
        build_options=config_dict,
        status="queued",
        bot_version=sc.current_bot_version or None,
        activation_token_hash=token_hash,
        activation_token_expires_at=now + timedelta(hours=settings.desktop_activation_token_ttl_hours),
        download_expires_at=now + timedelta(hours=settings.desktop_download_expires_hours),
    )
    session.add(new_build)
    await session.commit()
    await session.refresh(new_build)

    try:
        await github_actions.dispatch_workflow(
            build_id=str(new_build.id),
            user_id=str(user.id),
            client_id=next_client_id,
            api_url=api_url,
            activation_token=token,
            build_options=config_dict,
        )
    except Exception as exc:
        new_build.status = "failed"
        new_build.failure_reason = str(exc)[:500]
        await session.commit()
        await session.refresh(new_build)

    read = DesktopBuildRead.model_validate(new_build)
    return DesktopBuildWithToken(**read.model_dump(), activation_token=token)

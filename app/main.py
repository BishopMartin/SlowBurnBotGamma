import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.auth import auth_backend, fastapi_users
from app.database import async_session_maker
from app.models.system_config import SystemConfig
from app.routers import accounts, admin, auth_refresh, bot, config, desktop_builds, subscription, webhooks
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import github_actions
from app.settings import settings

logging.basicConfig(level=logging.INFO)


async def _sync_bot_version() -> None:
    """On startup, read BOT_VERSION from the main branch and update system_configs if newer."""
    if not settings.github_token or not settings.github_repo:
        return
    try:
        version = await github_actions.get_main_branch_bot_version()
        if not version:
            return
        async with async_session_maker() as session:
            sc = await session.scalar(select(SystemConfig))
            if sc is None:
                sc = SystemConfig()
                session.add(sc)
            def _gt(a: str, b: str) -> bool:
                try:
                    return [int(x) for x in a.split(".")] > [int(x) for x in b.split(".")]
                except Exception:
                    return False
            if sc.current_bot_version is None or _gt(version, sc.current_bot_version):
                sc.current_bot_version = version
                sc.current_bot_release_date = datetime.now(timezone.utc).strftime("%b %d %Y")
                await session.commit()
                logging.info(f"Bot version synced to {version}")
    except Exception as e:
        logging.warning(f"Startup bot version sync failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _sync_bot_version()
    yield


app = FastAPI(
    title="SlowBurnBot API",
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth routes: /auth/jwt/login, /auth/jwt/logout
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

# User management: /auth/register, /users/me, /users/{id}
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# App routers
app.include_router(auth_refresh.router)
app.include_router(accounts.router)
app.include_router(bot.router)
app.include_router(config.router)
app.include_router(admin.router)
app.include_router(subscription.router)
app.include_router(webhooks.router)
app.include_router(desktop_builds.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

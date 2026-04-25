import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import auth_backend, fastapi_users
from app.routers import accounts, admin, auth_refresh, bot, config, desktop_builds, subscription, webhooks
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.settings import settings

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="SlowBurnBot API",
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
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

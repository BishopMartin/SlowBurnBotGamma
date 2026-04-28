import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi_users import FastAPIUsers, BaseUserManager, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.user import User
from app.settings import settings

ACCESS_TOKEN_LIFETIME = 2592000  # 30 days


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    async def create(self, user_create, safe=False, request=None):
        from app.database import async_session_maker
        from app.models.invite_code import InviteCode

        code_str = getattr(user_create, "invite_code", None)
        if not code_str:
            raise HTTPException(status_code=400, detail="Registration code is required.")

        async with async_session_maker() as session:
            result = await session.execute(
                select(InviteCode).where(InviteCode.code == code_str)
            )
            invite = result.scalar_one_or_none()
            if invite is None:
                raise HTTPException(status_code=400, detail="Invalid registration code.")
            if invite.used_by_user_id is not None:
                raise HTTPException(status_code=400, detail="This registration code has already been used.")
            if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="This registration code has expired.")
            if invite.email and invite.email.lower() != user_create.email.lower():
                raise HTTPException(status_code=400, detail="This registration code is tied to a different email address.")

        user = await super().create(user_create, safe, request)
        return user

    async def on_after_register(self, user: User, request=None):
        from app.models.subscription import Subscription
        from app.models.invite_code import InviteCode
        from app.database import async_session_maker

        # Pull the invite code off the request body, if any.
        code_str: str | None = None
        if request:
            try:
                body = await request.json()
                raw = body.get("invite_code")
                if isinstance(raw, str) and raw.strip():
                    code_str = raw.strip()
            except Exception:
                pass

        async with async_session_maker() as session:
            invite: InviteCode | None = None

            if code_str:
                # Atomic claim: only succeeds if the invite is still unclaimed.
                # Wins the race against any concurrent registration with the
                # same code; the loser's super().create() user is deleted
                # below and the request fails.
                claim_stmt = (
                    update(InviteCode)
                    .where(
                        InviteCode.code == code_str,
                        InviteCode.used_by_user_id.is_(None),
                    )
                    .values(
                        used_by_user_id=user.id,
                        used_at=datetime.now(timezone.utc),
                    )
                    .returning(InviteCode)
                )
                claimed = await session.execute(claim_stmt)
                invite = claimed.scalar_one_or_none()

                if invite is None:
                    # Either the code never existed or another registration
                    # claimed it first.  Roll back the user that fastapi-users
                    # already committed before raising.
                    await session.execute(
                        delete(User).where(User.id == user.id)
                    )
                    await session.commit()
                    raise HTTPException(
                        status_code=400,
                        detail="This registration code has already been used.",
                    )

            sub_status = "inactive"
            plan_tier = "free"
            period_end = None

            if invite and invite.free_trial_days:
                sub_status = "trialing"
                plan_tier = invite.plan_tier
                period_end = datetime.now(timezone.utc) + timedelta(days=invite.free_trial_days)

                user_result = await session.execute(
                    select(User).where(User.id == user.id)
                )
                db_user = user_result.scalar_one_or_none()
                if db_user:
                    db_user.plan_tier = plan_tier

            subscription = Subscription(
                user_id=user.id,
                status=sub_status,
                plan_tier=plan_tier,
                current_period_end=period_end,
            )
            session.add(subscription)
            await session.commit()


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="/auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.secret_key, lifetime_seconds=ACCESS_TOKEN_LIFETIME)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
current_active_user_optional = fastapi_users.current_user(active=True, optional=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)

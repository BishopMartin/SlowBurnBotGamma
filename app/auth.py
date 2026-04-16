import uuid

from fastapi import Depends
from fastapi_users import FastAPIUsers, BaseUserManager, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.user import User
from app.settings import settings

ACCESS_TOKEN_LIFETIME = 3600  # 1 hour
REFRESH_TOKEN_LIFETIME = 86400 * 30  # 30 days


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    async def on_after_register(self, user: User, request=None):
        # Create a default subscription record for new users
        from app.models.subscription import Subscription
        from app.database import async_session_maker

        async with async_session_maker() as session:
            subscription = Subscription(user_id=user.id, status="inactive", plan_tier="free")
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
current_superuser = fastapi_users.current_user(active=True, superuser=True)

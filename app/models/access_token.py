import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AccessToken(Base):
    """Server-side session record backing the DatabaseStrategy auth backend
    (app/auth.py). The bearer token is now an opaque random string looked up
    here on every request, rather than a self-contained signed JWT — so
    logout and password-change can actually revoke it (delete the row)
    instead of it silently remaining valid until its natural expiry no
    matter what the user does.

    Structurally matches fastapi_users_db_sqlalchemy's
    SQLAlchemyBaseAccessTokenTableUUID (token/user_id/created_at), redefined
    here rather than inherited because that mixin hardcodes
    ForeignKey("user.id", ...) — this project's table is "users" (plural).
    """

    __tablename__ = "access_tokens"

    token: Mapped[str] = mapped_column(String(43), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

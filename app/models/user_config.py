import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserConfig(Base):
    """User-wide configuration (notification preferences, etc.)."""

    __tablename__ = "user_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )

    # Notification settings
    notices_type: Mapped[str] = mapped_column(String(10), default="email")  # text/email/both/none
    notices_session: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notify_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="config")

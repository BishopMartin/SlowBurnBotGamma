import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Account(Base):
    """A bot account (Instagram handle) managed by a user."""

    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(150))  # Instagram handle / internal name
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    group_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    proxy_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    proxy_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="accounts")
    settings: Mapped["AccountSettings | None"] = relationship(back_populates="account")
    session_logs: Mapped[list["SessionLog"]] = relationship(back_populates="account")
    activity_logs: Mapped[list["ActivityLog"]] = relationship(back_populates="account")
    follow_targets: Mapped[list["FollowTarget"]] = relationship(back_populates="account")

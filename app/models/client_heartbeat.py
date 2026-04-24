import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClientHeartbeat(Base):
    """Tracks live status of bot clients via periodic heartbeats."""

    __tablename__ = "client_heartbeats"
    __table_args__ = (
        UniqueConstraint("user_id", "client_id", name="uq_client_heartbeat_user_client"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    client_id: Mapped[int] = mapped_column(Integer)
    system_type: Mapped[str] = mapped_column(String(50), default="")
    ip_address: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(50), default="idle")
    current_account: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship()

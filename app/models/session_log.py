import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SessionLog(Base):
    """Structured session summary — mirrors the runlog sheet columns A–Q."""

    __tablename__ = "session_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )

    run_date: Mapped[date] = mapped_column(Date)
    run_sequence: Mapped[int] = mapped_column(Integer, default=1)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Four action slots
    action_1_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_1_count: Mapped[int] = mapped_column(Integer, default=0)
    action_2_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_2_count: Mapped[int] = mapped_column(Integer, default=0)
    action_3_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_3_count: Mapped[int] = mapped_column(Integer, default=0)
    action_4_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_4_count: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    account: Mapped["Account"] = relationship(back_populates="session_logs")

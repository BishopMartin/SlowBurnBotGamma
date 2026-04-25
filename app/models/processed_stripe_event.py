from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProcessedStripeEvent(Base):
    """Idempotency log for Stripe webhook events.

    Inserting a row keyed on Stripe's event id atomically claims that event;
    a duplicate delivery will hit the primary-key conflict and be skipped.
    """

    __tablename__ = "processed_stripe_events"

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

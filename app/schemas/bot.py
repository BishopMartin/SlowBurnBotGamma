"""Schemas for exe-facing bot endpoints."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel


class SessionLogCreate(BaseModel):
    account_id: uuid.UUID
    run_date: date
    run_sequence: int = 1
    start_time: datetime | None = None
    end_time: datetime | None = None
    action_1_type: str | None = None
    action_1_count: int = 0
    action_2_type: str | None = None
    action_2_count: int = 0
    action_3_type: str | None = None
    action_3_count: int = 0
    action_4_type: str | None = None
    action_4_count: int = 0
    error_message: str | None = None


class ActivityLogCreate(BaseModel):
    account_id: uuid.UUID
    kind: str  # "activity" | "error"
    action: str | None = None
    status: str | None = None
    details: str | None = None


class EntitlementRead(BaseModel):
    active: bool
    plan_tier: str
    current_period_end: datetime | None = None

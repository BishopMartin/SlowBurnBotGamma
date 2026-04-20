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


class CredentialsRead(BaseModel):
    ig_password: str | None = None


class IgnoreHandlesRead(BaseModel):
    handles: list[str]


class FollowTargetCreate(BaseModel):
    account_id: uuid.UUID
    target_handle: str
    source: str | None = None
    status: str = "following"
    follow_date: date | None = None


class FollowTargetUpdate(BaseModel):
    status: str | None = None
    unfollow_date: date | None = None
    follow_back: bool | None = None


class FollowTargetRead(BaseModel):
    id: uuid.UUID
    target_handle: str
    source: str | None
    status: str
    follow_date: date | None
    unfollow_date: date | None
    follow_back: bool | None


class RunCountRead(BaseModel):
    count: int


class BotUserConfigRead(BaseModel):
    notices_type: str
    notices_session: bool
    notify_email: str | None = None
    notify_phone: str | None = None

import uuid
from datetime import datetime

from pydantic import BaseModel


class UserConfigUpdate(BaseModel):
    like_suggested: bool | None = None
    like_sponsored: bool | None = None
    skip_login_check: bool | None = None
    login_tries: int | None = None
    notices_type: str = "none"
    notices_session: bool = True
    notices_login: bool = True
    notify_email: str | None = None
    notify_phone: str | None = None


class UserConfigRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    like_suggested: bool
    like_sponsored: bool
    skip_login_check: bool
    login_tries: int
    notices_type: str
    notices_session: bool
    notices_login: bool
    notify_email: str | None
    notify_phone: str | None
    updated_at: datetime

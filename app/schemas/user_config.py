import uuid
from datetime import datetime

from pydantic import BaseModel


class UserConfigUpdate(BaseModel):
    notices_type: str = "none"
    notices_session: bool = True
    notify_email: str | None = None
    notify_phone: str | None = None


class UserConfigRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    notices_type: str
    notices_session: bool
    notify_email: str | None
    notify_phone: str | None
    updated_at: datetime

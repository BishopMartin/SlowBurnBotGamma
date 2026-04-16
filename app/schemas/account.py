import uuid
from datetime import datetime

from pydantic import BaseModel


class AccountCreate(BaseModel):
    name: str
    enabled: bool = True
    group_number: int | None = None
    proxy_enabled: bool = False
    proxy_type: str | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    group_number: int | None = None
    proxy_enabled: bool | None = None
    proxy_type: str | None = None


class AccountRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    enabled: bool
    group_number: int | None
    proxy_enabled: bool
    proxy_type: str | None
    created_at: datetime
    updated_at: datetime

from datetime import datetime

from pydantic import BaseModel


class NotificationCredentialsUpdate(BaseModel):
    smtp_server: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None
    textbelt_key: str | None = None


class NotificationCredentialsRead(BaseModel):
    smtp_server: str
    smtp_port: int
    smtp_user: str | None
    smtp_password_set: bool
    textbelt_key_set: bool
    updated_at: datetime

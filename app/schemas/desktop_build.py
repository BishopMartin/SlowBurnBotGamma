import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class DesktopBuildConfig(BaseModel):
    """Customer-configurable settings seeded into the client INI on first run — no secrets."""

    client_name: str = Field(default="", max_length=15)
    system_type: Literal["windows", "linux"] = "windows"
    # Optional for linux (Chrome is installed in the Docker image at /usr/bin/google-chrome)
    chrome_path: str = Field(default="", max_length=500)
    chrome_version: str = Field(default="", max_length=20)
    chrome_user_data_dir_base: str = Field(default="PortableChrome", max_length=500)
    headless: bool = False
    detach: bool = False
    close_browser_session: bool = False
    close_browser_exit: bool = False
    bot_idle_delay: int = Field(default=5, ge=1, le=120)
    bot_debug: bool = False
    system_user_agent: str = Field(default="", max_length=500)
    add_arguments: Annotated[list[str], Field(default_factory=list, max_length=20)]
    api_url: str = Field(default="", max_length=500)

    @field_validator("add_arguments")
    @classmethod
    def validate_arguments(cls, v: list[str]) -> list[str]:
        for arg in v:
            if len(arg) > 200:
                raise ValueError("Each add_argument must be ≤ 200 characters")
        return v

    @model_validator(mode="after")
    def validate_platform(self) -> "DesktopBuildConfig":
        if self.system_type == "linux":
            # Chrome runs headlessly inside the Docker image; pyautogui window-focus not used
            self.headless = True
        elif self.system_type == "windows" and not self.chrome_path:
            raise ValueError("chrome_path is required for Windows builds")
        return self


class DesktopBuildCreate(BaseModel):
    config: DesktopBuildConfig
    slot_number: int | None = None  # if set, use this as client_id (rebuild preserving slot)


class DesktopBuildRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    client_id: int
    status: str
    build_options: dict
    failure_reason: str | None = None
    bot_version: str | None = None
    activated_at: datetime | None = None
    consumed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DesktopBuildWithToken(DesktopBuildRead):
    """Returned only on initial create/rebuild — includes the one-time activation token."""

    activation_token: str


class DesktopActivateRequest(BaseModel):
    user_id: uuid.UUID
    client_id: int
    activation_token: str = Field(..., min_length=1, max_length=200)
    bot_version: str = Field(default="", max_length=50)

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    environment: str = "production"

    # Stripe (optional until Phase 3)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_crawl: str = ""
    stripe_price_walk: str = ""
    stripe_price_run: str = ""

    # CORS (set once Next.js is deployed)
    cors_origins: list[str] = []

    # Public-facing API base URL (used as fallback when a desktop build config
    # omits api_url — baked into the EXE so it knows where to call home)
    public_api_url: str = ""

    # GitHub Actions — desktop build dispatch
    github_token: str = ""
    github_repo: str = ""            # "owner/repo"
    github_workflow_file: str = "build-desktop.yml"
    github_workflow_file_linux: str = "build-linux.yml"
    github_webhook_secret: str = ""  # optional; used by webhook receiver

    # GHCR — Linux Docker image delivery
    ghcr_namespace: str = ""  # e.g. "ghcr.io/bishopmartin/slowburnbotgamma"

    # Desktop build policy
    desktop_activation_token_ttl_hours: int = 168  # 7 days
    desktop_download_expires_hours: int = 72
    desktop_max_downloads: int = 10

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_async_driver(cls, v: str) -> str:
        # Railway injects postgresql:// — SQLAlchemy async needs postgresql+asyncpg://
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v


settings = Settings()

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

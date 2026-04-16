from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    environment: str = "production"

    # Stripe (optional until Phase 3)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # CORS (set once Next.js is deployed)
    cors_origins: list[str] = []


settings = Settings()

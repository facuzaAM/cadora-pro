import secrets
import warnings

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    APP_NAME: str = "Cadora API"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cadora"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    STORAGE_BUCKET: str = "cadora-documents"

    # JWT
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRATION_MINUTES: int = 15
    JWT_REFRESH_EXPIRATION_DAYS: int = 7
    JWT_EXPIRATION_HOURS: int = 24

    # Trusted hosts (comma-separated, for TrustedHostMiddleware)
    TRUSTED_HOSTS: str = "localhost,127.0.0.1,api,nginx,cadora.pro,app.cadora.pro,api.cadora.pro"

    # Database pool
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_BUSINESS: str = ""
    STRIPE_CANCEL_URL: str = "http://localhost:3000/billing"
    STRIPE_SUCCESS_URL: str = "http://localhost:3000/billing?success=true"

    # Upload limits
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".png", ".jpg", ".jpeg", ".tiff"]

    # CORS (JSON array)
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "https://cadora.pro", "https://app.cadora.pro"]

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "30/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_UPLOAD: str = "5/minute"

    # Logging
    LOG_FILE: str = ""
    LOG_LEVEL: str = "INFO"

    # Sentry (optional)
    SENTRY_DSN: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.JWT_SECRET:
            self.JWT_SECRET = secrets.token_hex(32)
            warnings.warn(
                "JWT_SECRET not set. Generated a random secret. "
                "Set JWT_SECRET in .env for persistence across restarts.",
                UserWarning,
            )


settings = Settings()

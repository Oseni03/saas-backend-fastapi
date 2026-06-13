from enum import StrEnum
from functools import lru_cache

from pydantic import AnyHttpUrl, EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────
    APP_NAME: str = "FastAPI SaaS"
    APP_ENV: Environment = Environment.DEVELOPMENT
    APP_SECRET_KEY: str
    APP_BASE_URL: AnyHttpUrl = "http://localhost:8000"  # type: ignore[assignment]
    FRONTEND_URL: AnyHttpUrl = "http://localhost:3000"  # type: ignore[assignment]

    # ── Database ─────────────────────────────────────
    DATABASE_URL: str

    # ── Redis ────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth / JWT ───────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── OAuth ────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # ── Email ────────────────────────────────────────
    RESEND_API_KEY: str = ""
    EMAIL_FROM: EmailStr = "noreply@yoursaas.com"  # type: ignore[assignment]
    EMAIL_FROM_NAME: str = "Your SaaS"

    # ── Paystack ──────────────────────────────────────
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_WEBHOOK_SECRET: str = ""
    PAYSTACK_PRO_PLAN_CODE: str = ""
    PAYSTACK_ENTERPRISE_PLAN_CODE: str = ""

    # ── Sentry ───────────────────────────────────────
    SENTRY_DSN: str = ""

    # ── Rate Limiting ────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Computed ─────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == Environment.DEVELOPMENT

    @field_validator("APP_SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("APP_SECRET_KEY must be at least 32 characters")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

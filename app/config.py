from dataclasses import dataclass, field
from enum import StrEnum
from functools import lru_cache
from typing import Literal

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


# ══════════════════════════════════════════════════════════════════════════
# Unified app config — hardcoded constants the whole app references
# ══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PasswordConfig:
    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = True
    require_digit: bool = True


@dataclass(frozen=True)
class RateLimitEntry:
    window_ms: int
    max: int


@dataclass(frozen=True)
class AuthRateLimitConfig:
    login: RateLimitEntry = field(default_factory=lambda: RateLimitEntry(window_ms=15 * 60 * 1000, max=10))
    register: RateLimitEntry = field(default_factory=lambda: RateLimitEntry(window_ms=60 * 60 * 1000, max=5))


@dataclass(frozen=True)
class PaginationConfig:
    default_limit: int = 20
    max_limit: int = 100


@dataclass(frozen=True)
class ExpiryConfig:
    invitation_days: int = 7
    password_reset_hours: int = 1
    verification_hours: int = 24


@dataclass(frozen=True)
class CorsConfig:
    methods: tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
    allowed_headers: tuple[str, ...] = ("Content-Type", "Authorization", "X-Request-ID")


@dataclass(frozen=True)
class GoogleOAuthConfig:
    auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url: str = "https://oauth2.googleapis.com/token"
    userinfo_url: str = "https://www.googleapis.com/oauth2/v3/userinfo"
    scope: str = "openid email profile"
    access_type: str = "offline"


@dataclass(frozen=True)
class GithubOAuthConfig:
    auth_url: str = "https://github.com/login/oauth/authorize"
    token_url: str = "https://github.com/login/oauth/access_token"
    user_url: str = "https://api.github.com/user"
    emails_url: str = "https://api.github.com/user/emails"
    scope: str = "read:user user:email"
    accept_header: str = "application/json"


@dataclass(frozen=True)
class OAuthConfig:
    google: GoogleOAuthConfig = field(default_factory=GoogleOAuthConfig)
    github: GithubOAuthConfig = field(default_factory=GithubOAuthConfig)


@dataclass(frozen=True)
class BillingConfig:
    paystack_api_base_url: str = "https://api.paystack.co"
    webhook_hmac_algorithm: str = "sha512"
    next_billing_month_offset: int = 1


@dataclass(frozen=True)
class LoggingConfig:
    service_name: str = "fastapi-saas"
    dev_level: str = "debug"
    prod_level: str = "info"
    ignore_paths: tuple[str, ...] = ("/api/v1/health", "/api/v1/ready", "/favicon.ico")


@dataclass(frozen=True)
class PlanLimitEntry:
    max_members: int | None
    max_projects: int | None
    audit_log_retention_days: int
    mfa_required: bool
    sso_enabled: bool
    priority_support: bool


@dataclass(frozen=True)
class PlanLimitsConfig:
    FREE: PlanLimitEntry = field(default_factory=lambda: PlanLimitEntry(
        max_members=5, max_projects=3, audit_log_retention_days=7,
        mfa_required=False, sso_enabled=False, priority_support=False,
    ))
    PRO: PlanLimitEntry = field(default_factory=lambda: PlanLimitEntry(
        max_members=50, max_projects=None, audit_log_retention_days=90,
        mfa_required=False, sso_enabled=False, priority_support=True,
    ))
    ENTERPRISE: PlanLimitEntry = field(default_factory=lambda: PlanLimitEntry(
        max_members=None, max_projects=None, audit_log_retention_days=365,
        mfa_required=True, sso_enabled=True, priority_support=True,
    ))


@dataclass(frozen=True)
class DbPoolConfig:
    pool_size: int = 10
    max_overflow: int = 20


@dataclass(frozen=True)
class JwtConfig:
    algorithm: str = "HS256"
    access_token_type: str = "access"
    refresh_token_type: str = "refresh"
    mfa_pending_token_type: str = "mfa_pending"


@dataclass(frozen=True)
class MfaConfig:
    issuer_name: str = "FastAPI SaaS"
    valid_window: int = 1
    pending_token_expires_in: str = "5m"
    pending_expires_in_seconds: int = 300


@dataclass(frozen=True)
class ProjectConfig:
    # ── App metadata ──────────────────────────────────
    name: str = "FastAPI SaaS"
    version: str = "1.0.0"
    api_prefix: str = "/api/v1"

    # ── Auth ──────────────────────────────────────────
    password: PasswordConfig = field(default_factory=PasswordConfig)
    bcrypt_rounds: int = 12
    token_type: Literal["bearer"] = "bearer"
    auth_scheme: str = "Bearer"
    secure_token_bytes: int = 32

    # ── JWT ───────────────────────────────────────────
    jwt: JwtConfig = field(default_factory=JwtConfig)

    # ── MFA ───────────────────────────────────────────
    mfa: MfaConfig = field(default_factory=MfaConfig)

    # ── Rate limiting ─────────────────────────────────
    rate_limit: AuthRateLimitConfig = field(default_factory=AuthRateLimitConfig)
    rate_limit_period: str = "minute"

    # ── Pagination ────────────────────────────────────
    pagination: PaginationConfig = field(default_factory=PaginationConfig)

    # ── Expiry durations ──────────────────────────────
    expiry: ExpiryConfig = field(default_factory=ExpiryConfig)

    # ── JSON body limit ───────────────────────────────
    json_body_limit: str = "1mb"

    # ── CORS ──────────────────────────────────────────
    cors: CorsConfig = field(default_factory=CorsConfig)

    # ── Role rankings ─────────────────────────────────
    role_rank: dict[str, int] = field(default_factory=lambda: {
        "VIEWER": 0,
        "MEMBER": 1,
        "ADMIN": 2,
        "OWNER": 3,
    })

    # ── OAuth provider URLs ───────────────────────────
    oauth: OAuthConfig = field(default_factory=OAuthConfig)

    # ── Billing ───────────────────────────────────────
    billing: BillingConfig = field(default_factory=BillingConfig)

    # ── Logging ───────────────────────────────────────
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # ── Plan limits ───────────────────────────────────
    plan_limits: PlanLimitsConfig = field(default_factory=PlanLimitsConfig)

    # ── Database pool ─────────────────────────────────
    db: DbPoolConfig = field(default_factory=DbPoolConfig)

    # ── Other ─────────────────────────────────────────
    sentry_traces_sample_rate: float = 0.1
    health_check_paths: tuple[str, ...] = ("/api/v1/health", "/api/v1/ready")
    graceful_shutdown_timeout_ms: int = 10_000


project = ProjectConfig()

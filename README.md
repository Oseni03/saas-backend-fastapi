# FastAPI SaaS Boilerplate

A production-ready FastAPI backend with authentication, multi-tenant organizations, Stripe billing, transactional email, notifications, and full observability.

## Features

| Feature | Details |
|---|---|
| **Auth** | Register, login, JWT access + refresh tokens, email verification, password reset, Google/GitHub OAuth, MFA-ready |
| **Organizations** | Multi-tenant with member roles (Owner, Admin, Member, Viewer), invite-by-email flow |
| **Billing** | Stripe Checkout, Billing Portal, webhook handling, plan sync (Free / Pro / Enterprise) |
| **Email** | Resend integration — verification, password reset, invitations, welcome email |
| **Notifications** | In-app notification center with read/unread state |
| **Audit Log** | Every sensitive action is logged with actor, resource, and IP |
| **Observability** | Structured logging (structlog), Sentry error tracking, request ID tracing |
| **Rate Limiting** | SlowAPI with per-IP limits, configurable via env |
| **Security** | bcrypt passwords, hashed one-time tokens, CORS, request ID middleware |

## Project Structure

```
app/
├── api/v1/endpoints/   # Thin route handlers
├── services/           # Business logic (framework-agnostic)
├── repositories/       # DB access layer
├── models/             # SQLAlchemy ORM models
├── schemas/            # Pydantic request/response schemas
├── core/               # Security, exceptions
├── db/                 # Session, base, migrations (Alembic)
└── lib/                # Logger, email, ULID helpers
```

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your secrets

# 2. Start services
make dev

# 3. Run migrations
make db-migrate

# 4. Seed dev data
make db-seed

# 5. Visit docs
open http://localhost:8000/docs
```

## Key API Endpoints

```
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/verify-email
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
GET  /api/v1/auth/me

GET    /api/v1/users/me
PATCH  /api/v1/users/me
POST   /api/v1/users/me/change-password
DELETE /api/v1/users/me

POST   /api/v1/organizations
GET    /api/v1/organizations
GET    /api/v1/organizations/{id}
PATCH  /api/v1/organizations/{id}
DELETE /api/v1/organizations/{id}
POST   /api/v1/organizations/{id}/invitations
POST   /api/v1/organizations/invitations/accept
PATCH  /api/v1/organizations/{id}/members/{user_id}
DELETE /api/v1/organizations/{id}/members/{user_id}

POST /api/v1/billing/organizations/{id}/checkout
POST /api/v1/billing/organizations/{id}/portal
POST /api/v1/billing/webhooks/stripe

GET  /api/v1/notifications
POST /api/v1/notifications/{id}/read
POST /api/v1/notifications/read-all

GET /api/v1/health
GET /api/v1/ready
```

## Development Commands

```bash
make test          # Run tests with coverage
make lint          # Ruff lint
make format        # Ruff format
make typecheck     # mypy
make db-revision msg="add foo table"  # New migration
make db-migrate    # Apply migrations
make db-seed       # Seed local data
```

## Architecture Decisions

- **ULID primary keys** — sortable, URL-safe, no UUID/integer tradeoffs
- **Repository pattern** — DB queries isolated and mockable
- **Service layer** — business logic is pure Python, no FastAPI coupling
- **Thin routes** — routes only parse input and call services
- **Hashed tokens** — verification/reset tokens stored as SHA-256 hashes
- **Async throughout** — asyncpg + SQLAlchemy async engine

# FastAPI SaaS Boilerplate

A production-ready FastAPI backend with authentication, multi-tenant organizations, Stripe billing, transactional email, notifications, and full observability.

## Features

| Feature           | Details                                                                                                          |
| ----------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Auth**          | Register, login, JWT access + refresh tokens, email verification, password reset, Google/GitHub OAuth, MFA-ready |
| **Organizations** | Multi-tenant with member roles (Owner, Admin, Member, Viewer), invite-by-email flow                              |
| **Billing**       | Stripe Checkout, Billing Portal, webhook handling, plan sync (Free / Pro / Enterprise)                           |
| **Email**         | Resend integration — verification, password reset, invitations, welcome email                                    |
| **Notifications** | In-app notification center with read/unread state                                                                |
| **Audit Log**     | Every sensitive action is logged with actor, resource, and IP                                                    |
| **Observability** | Structured logging (structlog), Sentry error tracking, request ID tracing                                        |
| **Rate Limiting** | SlowAPI with per-IP limits, configurable via env                                                                 |
| **Security**      | bcrypt passwords, hashed one-time tokens, CORS, request ID middleware                                            |

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

### 1️⃣ Clone the Repository

```bash
git clone <your-repo-url>
cd <project-folder>
```

---

## 2️⃣ Create Virtual Environment

```bash
uv venv
source venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows
```

---

### 3️⃣ Install Dependencies

```bash
uv pip install -r requirements.txt
```

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory:

```env
# ── App ──────────────────────────────────────────────
APP_NAME="FastAPI SaaS"
APP_ENV=development                  # development | staging | production
APP_SECRET_KEY=changeme-use-openssl-rand-hex-32
APP_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# ── Database ──────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/saas_db

# ── Redis ─────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── Auth / JWT ────────────────────────────────────────
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# ── OAuth ─────────────────────────────────────────────
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# ── Email (Resend) ────────────────────────────────────
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
EMAIL_FROM="noreply@yoursaas.com"
EMAIL_FROM_NAME="Your SaaS"

# ── Billing (Paystack) ────────────────────────────────
PAYSTACK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxx
PAYSTACK_WEBHOOK_SECRET=your-webhook-secret-phrase
PAYSTACK_PRO_PLAN_CODE=PLN_xxxxxxxxxxxxxxxxxxxx
PAYSTACK_ENTERPRISE_PLAN_CODE=PLN_xxxxxxxxxxxxxxxxxxxx

# ── Sentry ────────────────────────────────────────────
SENTRY_DSN=

# ── Rate Limiting ─────────────────────────────────────
RATE_LIMIT_PER_MINUTE=60
```

### 4️⃣ Run Migrations

```bash
alembic upgrade head
```

### 5️⃣ Start the Server

```bash
fastapi run main.py
```

## Key API Endpoints

```

POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/verify-email
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
GET /api/v1/auth/me

GET /api/v1/users/me
PATCH /api/v1/users/me
POST /api/v1/users/me/change-password
DELETE /api/v1/users/me

POST /api/v1/organizations
GET /api/v1/organizations
GET /api/v1/organizations/{id}
PATCH /api/v1/organizations/{id}
DELETE /api/v1/organizations/{id}
POST /api/v1/organizations/{id}/invitations
POST /api/v1/organizations/invitations/accept
PATCH /api/v1/organizations/{id}/members/{user_id}
DELETE /api/v1/organizations/{id}/members/{user_id}

POST /api/v1/billing/organizations/{id}/checkout
POST /api/v1/billing/organizations/{id}/portal
POST /api/v1/billing/webhooks/stripe

GET /api/v1/notifications
POST /api/v1/notifications/{id}/read
POST /api/v1/notifications/read-all

GET /api/v1/health
GET /api/v1/ready

```

## Development Commands

```bash
alembic revision --autogenerate -m "describe_change"  # New migration
alembic upgrade head                                   # Apply migrations
alembic downgrade -1                                   # Roll back last migration
python scripts/seed.py                                 # Seed local data
pytest -v --cov=app --cov-report=term-missing          # Run tests
ruff check app tests                                   # Lint
ruff format app tests                                  # Format
mypy app                                               # Type check
```

## Architecture Decisions

- **ULID primary keys** — sortable, URL-safe, no UUID/integer tradeoffs
- **Repository pattern** — DB queries isolated and mockable
- **Service layer** — business logic is pure Python, no FastAPI coupling
- **Thin routes** — routes only parse input and call services
- **Hashed tokens** — verification/reset tokens stored as SHA-256 hashes
- **Async throughout** — asyncpg + SQLAlchemy async engine

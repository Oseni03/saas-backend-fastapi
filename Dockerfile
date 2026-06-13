FROM python:3.11-slim AS base

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache .

COPY . .

# ── Development ──────────────────────────────────────────────────────
FROM base AS dev
RUN uv pip install --system --no-cache ".[dev]"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production ───────────────────────────────────────────────────────
FROM base AS prod
RUN adduser --disabled-password --gecos "" appuser
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

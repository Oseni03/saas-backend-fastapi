.PHONY: dev stop db-migrate db-seed test lint format typecheck

## ── Local dev ────────────────────────────────────────────────────────

dev:
	docker compose up --build

stop:
	docker compose down

## ── Database ─────────────────────────────────────────────────────────

db-migrate:
	alembic upgrade head

db-rollback:
	alembic downgrade -1

db-revision:
	alembic revision --autogenerate -m "$(msg)"

db-seed:
	python scripts/seed.py

## ── Testing ──────────────────────────────────────────────────────────

test:
	pytest -v --cov=app --cov-report=term-missing

test-watch:
	pytest -v --cov=app -f

## ── Code quality ─────────────────────────────────────────────────────

lint:
	ruff check app tests

format:
	ruff format app tests

typecheck:
	mypy app

check: lint typecheck

## ── Stripe (local webhook forwarding) ───────────────────────────────

stripe:
	docker compose --profile stripe up stripe-cli

.PHONY: help install dev test lint format migrate seed docker-up docker-down check-prod verify

help:
	@echo "Available commands:"
	@echo "  make install     Install dependencies"
	@echo "  make dev         Start dev server"
	@echo "  make test        Run tests"
	@echo "  make lint        Run linters"
	@echo "  make format      Format code"
	@echo "  make migrate     Run database migrations (alembic upgrade head)"
	@echo "  make seed        Seed sample data"
	@echo "  make check-prod  Validate production configuration"
	@echo "  make verify      HTTP post-deploy checks (BASE_URL=...)"
	@echo "  make docker-up   Start Docker services"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --port 8000

test:
	pytest tests/unit tests/scenarios -v

lint:
	ruff check app/ tests/

format:
	ruff format app/ tests/

migrate:
	alembic upgrade head

seed:
	python -m app.core.seed

check-prod:
	python -m app.cli.check_prod --force-prod

verify:
	@BASE_URL=$${BASE_URL:-http://127.0.0.1:8000}; \
	curl -fsS $$BASE_URL/health/live >/dev/null && echo OK live; \
	curl -fsS $$BASE_URL/health/ready >/dev/null && echo OK ready; \
	curl -fsS $$BASE_URL/api/v1/me >/dev/null && echo OK me

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

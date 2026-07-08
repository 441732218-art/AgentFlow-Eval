.PHONY: help install dev test lint format migrate seed docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install    Install dependencies"
	@echo "  make dev        Start dev server"
	@echo "  make test       Run tests"
	@echo "  make lint       Run linters"
	@echo "  make format     Format code"
	@echo "  make migrate    Run database migrations"
	@echo "  make seed       Seed sample data"
	@echo "  make docker-up  Start Docker services"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --port 8000

test:
	pytest tests/ -v

lint:
	ruff check app/ tests/

format:
	ruff format app/ tests/

migrate:
	alembic upgrade head

seed:
	python -m app.core.seed

docker-up:
	docker compose up -d

docker-down:
	docker compose down

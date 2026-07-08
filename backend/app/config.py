# (c) 2026 AgentFlow-Eval
"""Application configuration using pydantic-settings with environment modes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Production-grade configuration with dev/test/prod separation.

    Environment variables override .env values which override defaults.
    """

    # ---- Environment ----
    ENV: Literal["dev", "test", "prod"] = "dev"
    DEBUG: bool = True
    APP_NAME: str = "AgentFlow-Eval"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-production"

    # ---- CORS ----
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # ---- Database ----
    DATABASE_URL: str = "sqlite+aiosqlite:///./agentflow_eval.db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_ECHO: bool = False

    # ---- Redis / Celery ----
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # ---- OpenAI ----
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # ---- Logging ----
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/agentflow_eval.log"
    LOG_FORMAT: Literal["json", "text"] = "text"
    LOG_MAX_BYTES: int = 10485760  # 10 MB
    LOG_BACKUP_COUNT: int = 30

    # ---- Rate Limiting ----
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # ---- Request Limits ----
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10 MB

    # ---- Pagination ----
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # ---- Gunicorn ----
    GUNICORN_WORKERS: int = 4
    GUNICORN_WORKER_CLASS: str = "uvicorn.workers.UvicornWorker"
    GUNICORN_TIMEOUT: int = 120

    @property
    def is_dev(self) -> bool:
        return self.ENV == "dev"

    @property
    def is_prod(self) -> bool:
        return self.ENV == "prod"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()

# Ensure log directory exists
Path(settings.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

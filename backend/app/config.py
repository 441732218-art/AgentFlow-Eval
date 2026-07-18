# (c) 2026 AgentFlow-Eval
"""Application configuration using pydantic-settings with environment modes."""

from __future__ import annotations

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
    APP_NAME: str = "AgentFlow Intelligence"
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

    # ---- Logging (AOLS) ----
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/agentflow_eval.log"
    # Prefer "json" in prod; text keeps human-readable local dev consoles
    LOG_FORMAT: Literal["json", "text"] = "text"
    LOG_MAX_BYTES: int = 10485760  # 10 MB
    LOG_BACKUP_COUNT: int = 30
    LOG_SERVICE_NAME: str = "agentflow-api"
    # Skip high-frequency paths in access logs (comma-separated prefixes)
    LOG_ACCESS_SKIP_PATHS: str = "/health,/metrics,/favicon.ico"
    # Max string length when redacting nested log values
    LOG_REDACT_MAX_STR: int = 2000
    # Persist structured events to agent_logs table (best-effort batch)
    LOG_DB_SINK: bool = True
    LOG_DB_BATCH_SIZE: int = 32
    LOG_DB_FLUSH_INTERVAL_SEC: float = 1.0
    # Retention hint for cleanup jobs (days); 0 = no auto cleanup in v1
    LOG_DB_RETENTION_DAYS: int = 30

    # ---- Rate Limiting ----
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # ---- Auth (API Key) ----
    # When AUTH_ENABLED=true, all /api/v1/* routes require X-API-Key or Bearer token.
    # API_KEYS examples:
    #   "dev-secret"
    #   "dev-secret:alice"
    #   "dev-secret:alice:manager,prod-secret:bob:user"
    AUTH_ENABLED: bool = False
    API_KEYS: str = ""

    # ---- RBAC ----
    # When true (and AUTH_ENABLED), enforce role permissions on API endpoints.
    RBAC_ENABLED: bool = True
    # Default role for actors without ACTOR_ROLES / key-embedded role.
    DEFAULT_ROLE: str = "user"
    # Optional actor→role map: "alice:manager,bob:reviewer"
    ACTOR_ROLES: str = ""

    # ---- Tenancy (actor isolation) ----
    # When AUTH_ENABLED or TENANCY_ENABLED is true, tasks are scoped by created_by.
    TENANCY_ENABLED: bool = False
    # Comma-separated actors that can see all tasks, e.g. "admin,ops"
    # These actors also resolve to Role.ADMIN when no explicit role is set.
    ADMIN_ACTORS: str = "admin"

    # ---- Tool sandbox ----
    TOOL_TIMEOUT_SEC: float = 3.0

    # ---- Request Limits ----
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10 MB

    # ---- Pagination ----
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # ---- Gunicorn ----
    GUNICORN_WORKERS: int = 4
    GUNICORN_WORKER_CLASS: str = "uvicorn.workers.UvicornWorker"
    GUNICORN_TIMEOUT: int = 120

    # ---- Judge engine ----
    # Soft timeout (seconds) for a single evaluate() call; 0 disables.
    JUDGE_TIMEOUT_SEC: float = 60.0
    # In-process result cache size (LRU).
    JUDGE_CACHE_SIZE: int = 128

    # ---- Observability (Prometheus) ----
    METRICS_ENABLED: bool = True

    # ---- Cache (L1 memory + L2 Redis) ----
    CACHE_ENABLED: bool = True
    CACHE_WARMUP_ON_STARTUP: bool = False

    # ---- Resilience (LLM / external calls) ----
    LLM_RETRY_ENABLED: bool = True
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_MIN_WAIT_SEC: float = 1.0
    LLM_RETRY_MAX_WAIT_SEC: float = 10.0
    LLM_CALL_TIMEOUT_SEC: float = 30.0
    CIRCUIT_ENABLED: bool = True
    CIRCUIT_FAILURE_THRESHOLD: int = 5
    CIRCUIT_RECOVERY_TIMEOUT_SEC: float = 60.0

    # ---- Multimodal storage & vision ----
    # local | s3 | minio
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "data/uploads"
    S3_BUCKET: str = "agentflow"
    S3_ENDPOINT_URL: str = ""  # e.g. http://localhost:9000 for MinIO
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "us-east-1"
    S3_PREFIX: str = ""
    # Max upload size for multimodal files (bytes)
    MEDIA_MAX_UPLOAD_BYTES: int = 20 * 1024 * 1024  # 20 MB
    # Vision multimodal model (OpenAI-compatible)
    VISION_MODEL: str = "gpt-4o-mini"

    # ---- Deploy profiles (lite | private | saas | auto) ----
    # lite: SQLite + eager queue + memory cache + in-process bus (zero Redis)
    # private: full middleware (default)
    # saas: private + billing hooks enabled when BILLING_ENABLED
    # auto: lite if sqlite+eager else private
    DEPLOY_PROFILE: str = "auto"
    # celery | eager | memory  (empty = profile default)
    TASK_QUEUE_BACKEND: str = ""
    # SaaS metering (tables land in later migration; noop until then)
    BILLING_ENABLED: bool = False
    # Stripe Checkout (mock by default — no real charges without keys)
    # mock | live
    STRIPE_MODE: str = "mock"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_SUCCESS_URL: str = "http://localhost:5173/billing?checkout=success"
    STRIPE_CANCEL_URL: str = "http://localhost:5173/billing?checkout=cancel"
    # Optional price id map: "pro:price_xxx,enterprise:price_yyy"
    STRIPE_PRICE_IDS: str = ""
    # Slow-task threshold for observability sampling (seconds)
    SLOW_TASK_THRESHOLD_SEC: float = 30.0
    OBSERVABILITY_KPI_ENABLED: bool = True

    # ---- Plugins ----
    # Master switch for discovery/load on startup.
    PLUGINS_ENABLED: bool = True
    # Comma-separated directories to scan (relative to CWD or absolute).
    # Example: "plugins,./external_plugins"
    PLUGIN_DIRS: str = "plugins"
    # Comma-separated Python entries: "pkg.mod:Plugin,app.plugins.examples.echo_tool:Plugin"
    PLUGIN_MODULES: str = ""
    # Optional local marketplace catalog JSON path.
    PLUGIN_CATALOG_PATH: str = ""
    # When true, seed example plugins into the in-memory market catalog.
    PLUGIN_MARKET_SEED_EXAMPLES: bool = True
    # When true, only load modules listed in PLUGIN_MODULES (ignore PLUGIN_DIRS scan).
    # Production hardening: set PLUGIN_MODULES=pkg:Plugin,... and PLUGIN_STRICT_ALLOWLIST=true
    PLUGIN_STRICT_ALLOWLIST: bool = False
    # Optional extra allowlist of module prefixes or full entries (comma-separated).
    # Empty = only PLUGIN_MODULES when strict; when not strict, no extra filter.
    PLUGIN_ALLOWLIST: str = ""

    @property
    def plugin_dir_list(self) -> list[str]:
        raw = (self.PLUGIN_DIRS or "").strip()
        if not raw:
            return []
        return [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]

    @property
    def plugin_module_list(self) -> list[str]:
        raw = (self.PLUGIN_MODULES or "").strip()
        if not raw:
            return []
        return [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]

    @property
    def plugin_allowlist(self) -> list[str]:
        raw = (self.PLUGIN_ALLOWLIST or "").strip()
        if not raw:
            return []
        return [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]

    @property
    def is_dev(self) -> bool:
        return self.ENV == "dev"

    @property
    def is_test(self) -> bool:
        return self.ENV == "test"

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

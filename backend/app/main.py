# (c) 2026 AgentFlow-Eval
"""FastAPI application entry point with production middleware stack."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.config import settings
from app.utils.exceptions import AgentFlowError, error_response
from app.utils.logger import setup_logging
from app.core.middleware import APIKeyAuthMiddleware, RequestIDMiddleware

setup_logging()

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    HAS_SLOWAPI = True
except ImportError:
    HAS_SLOWAPI = False


# ---- Lifespan events ----
def _sqlite_table_columns(connection, table: str) -> set[str]:
    from sqlalchemy import text

    rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _ensure_sqlite_columns(connection) -> None:
    """Add missing columns on existing SQLite DBs (create_all never ALTERs)."""
    from sqlalchemy import text
    import logging

    log = logging.getLogger(__name__)
    if connection.dialect.name != "sqlite":
        return

    task_cols = {
        "celery_task_id": "ALTER TABLE tasks ADD COLUMN celery_task_id VARCHAR(255)",
        "is_archived": "ALTER TABLE tasks ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0",
        "created_by": "ALTER TABLE tasks ADD COLUMN created_by VARCHAR(100) NOT NULL DEFAULT 'anonymous'",
    }
    existing = _sqlite_table_columns(connection, "tasks")
    for name, ddl in task_cols.items():
        if name not in existing:
            connection.execute(text(ddl))
            log.info("SQLite backfill: tasks.%s", name)

    if "traces" in {
        r[0]
        for r in connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
    }:
        trace_cols = {
            "prompt_tokens": "ALTER TABLE traces ADD COLUMN prompt_tokens INTEGER NOT NULL DEFAULT 0",
            "completion_tokens": "ALTER TABLE traces ADD COLUMN completion_tokens INTEGER NOT NULL DEFAULT 0",
            "cost": "ALTER TABLE traces ADD COLUMN cost FLOAT NOT NULL DEFAULT 0",
            "agent_version": "ALTER TABLE traces ADD COLUMN agent_version VARCHAR(100)",
            "prompt_version": "ALTER TABLE traces ADD COLUMN prompt_version VARCHAR(100)",
            "model_version": "ALTER TABLE traces ADD COLUMN model_version VARCHAR(100)",
            "tool_version": "ALTER TABLE traces ADD COLUMN tool_version VARCHAR(100)",
        }
        existing = _sqlite_table_columns(connection, "traces")
        for name, ddl in trace_cols.items():
            if name not in existing:
                connection.execute(text(ddl))
                log.info("SQLite backfill: traces.%s", name)

    if "metric_scores" in {
        r[0]
        for r in connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
    }:
        ms_cols = {
            "confidence": "ALTER TABLE metric_scores ADD COLUMN confidence FLOAT",
            "is_human_reviewed": "ALTER TABLE metric_scores ADD COLUMN is_human_reviewed BOOLEAN NOT NULL DEFAULT 0",
            "human_score": "ALTER TABLE metric_scores ADD COLUMN human_score FLOAT",
            "reviewer": "ALTER TABLE metric_scores ADD COLUMN reviewer VARCHAR(100)",
        }
        existing = _sqlite_table_columns(connection, "metric_scores")
        for name, ddl in ms_cols.items():
            if name not in existing:
                connection.execute(text(ddl))
                log.info("SQLite backfill: metric_scores.%s", name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    from app.models.base import Base
    from app.core.dependencies import engine
    import logging

    log = logging.getLogger(__name__)
    # Import models so metadata is complete (incl. AuditLog)
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.run_sync(_ensure_sqlite_columns)
        except Exception as exc:
            log.warning("Schema backfill skipped: %s", exc)
    log.info("Tables initialized")

    # Live activity WebSocket hub (Redis pub/sub + in-process fan-out)
    ws_started = False
    try:
        from app.core.ws_hub import start_ws_hub, stop_ws_hub

        await start_ws_hub()
        ws_started = True
    except Exception as exc:
        log.warning("WS hub start failed: %s", exc)

    yield

    if ws_started:
        try:
            from app.core.ws_hub import stop_ws_hub

            await stop_ws_hub()
        except Exception as exc:
            log.warning("WS hub stop failed: %s", exc)

    await engine.dispose()
    from app.core.dependencies import close_redis
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    description="Agent automated evaluation platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_prod else None,
    redoc_url="/redoc" if not settings.is_prod else None,
)

# ---- Rate limiting ----
if HAS_SLOWAPI and settings.RATE_LIMIT_ENABLED:
    limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])
    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_exceeded_handler)

# Middleware order: last added = outermost. Desired stack:
#   CORS -> RequestID -> APIKeyAuth -> app
app.add_middleware(APIKeyAuthMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-API-Key"],
    expose_headers=["X-Request-ID"],
)

# ---- Trusted hosts ----
if settings.is_prod:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# ---- Routes ----
app.include_router(v1_router)


# ---- Exception handlers ----
@app.exception_handler(AgentFlowError)
async def agentflow_error_handler(request: Request, exc: AgentFlowError) -> JSONResponse:
    rid = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.status_code, exc.message, exc.detail, request_id=rid),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import traceback
    rid = getattr(request.state, "request_id", None)
    stack = traceback.format_exc() if settings.DEBUG else None
    return JSONResponse(
        status_code=500,
        content=error_response(500, "Internal error", str(exc) if settings.DEBUG else None, request_id=rid, stacktrace=stack),
    )


# ---- Health check ----
@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint with database and Redis connectivity checks."""
    from sqlalchemy import text
    from app.core.dependencies import engine
    services = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"] = "ok"
    except Exception as e:
        services["database"] = f"error: {e}"
    if settings.CELERY_TASK_ALWAYS_EAGER:
        # Local mode: never block health on Redis
        services["redis"] = "skipped (CELERY_TASK_ALWAYS_EAGER)"
    else:
        try:
            from app.core.dependencies import get_redis
            r = await get_redis()
            await r.ping()
            services["redis"] = "ok"
        except Exception:
            services["redis"] = "unavailable"
    critical_ok = services.get("database") == "ok"
    redis_ok = services.get("redis", "").startswith(("ok", "skipped"))
    all_healthy = critical_ok and redis_ok
    return {
        "status": "healthy" if all_healthy else "degraded",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "services": services,
        "celery_eager": settings.CELERY_TASK_ALWAYS_EAGER,
    }

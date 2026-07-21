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
from app.core.middleware import (
    APIKeyAuthMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.observability.metrics import MetricsMiddleware, get_metrics_response
from app.core.settings_guard import enforce_production_settings

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
        "tenant_id": "ALTER TABLE tasks ADD COLUMN tenant_id VARCHAR(36)",
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

    # Fail fast on insecure production configuration
    try:
        enforce_production_settings(settings)
    except Exception:
        log.exception("Production settings validation failed")
        raise

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

    # Optional multi-layer cache warm-up (settings / dashboard / recent tasks)
    if getattr(settings, "CACHE_WARMUP_ON_STARTUP", False):
        try:
            from app.core.cache.warmup import warm_cache

            summary = await warm_cache(actor="anonymous", limit=20)
            log.info("Cache warmup: %s", summary)
        except Exception as exc:
            log.warning("Cache warmup skipped: %s", exc)

    # Deploy profile: bind TaskQueue / Cache / EventBus / Metering ports
    try:
        from app.core.profiles import apply_profile_from_settings, profile_status

        apply_profile_from_settings()
        log.info("Infrastructure ports: %s", profile_status())
    except Exception as exc:
        log.warning("Deploy profile apply failed (using lazy defaults): %s", exc)

    # Plugin system: discover directories + explicit modules
    plugins_bootstrapped = False
    try:
        from app.core.plugins.manager import get_plugin_manager
        from app.core.plugins.market import get_plugin_market

        if getattr(settings, "PLUGINS_ENABLED", True):
            mgr = get_plugin_manager()
            strict = bool(
                getattr(settings, "PLUGIN_STRICT_ALLOWLIST", False)
                or getattr(settings, "PLUGIN_STRICT_MODE", False)
            )
            modules = list(getattr(settings, "plugin_module_list", []) or [])
            directories = list(getattr(settings, "plugin_dir_list", []) or [])
            if strict:
                # Production hardening: only explicit modules, never directory scan
                directories = []
                if not modules:
                    log.warning(
                        "PLUGIN_STRICT_MODE/ALLOWLIST=true but PLUGIN_MODULES empty — no plugins loaded"
                    )
            # Optional HMAC signature gate
            try:
                from app.core.plugins.signature import (
                    filter_signed_modules,
                    signature_check_enabled,
                )

                if signature_check_enabled() and modules:
                    modules, rejected = filter_signed_modules(modules)
                    if rejected:
                        log.warning(
                            "Plugin signature rejections: %s", rejected
                        )
            except Exception as sig_exc:
                log.warning("Plugin signature check skipped: %s", sig_exc)
            summary = mgr.bootstrap(
                enabled=True,
                directories=directories,
                modules=modules,
                auto_activate=True,
                allowlist=list(getattr(settings, "plugin_allowlist", []) or [])
                or (modules if strict else None),
            )
            plugins_bootstrapped = True
            log.info(
                "Plugins bootstrap (strict=%s): %s",
                strict,
                summary,
            )
            market = get_plugin_market()
            if getattr(settings, "PLUGIN_MARKET_SEED_EXAMPLES", True):
                market.seed_builtin_catalog()
            catalog = getattr(settings, "PLUGIN_CATALOG_PATH", "") or ""
            if catalog:
                market.catalog_path = __import__("pathlib").Path(catalog)
                market.load_catalog()
        else:
            log.info("Plugin system disabled (PLUGINS_ENABLED=false)")
    except Exception as exc:
        log.warning("Plugin bootstrap skipped: %s", exc)

    yield

    if plugins_bootstrapped:
        try:
            from app.core.plugins.manager import get_plugin_manager

            get_plugin_manager().shutdown()
        except Exception as exc:
            log.warning("Plugin shutdown failed: %s", exc)

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
    version="1.0.0",
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
#   CORS -> RequestID -> SecurityHeaders -> Metrics -> APIKeyAuth -> app
app.add_middleware(APIKeyAuthMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Trace-ID",
        "X-API-Key",
    ],
    expose_headers=["X-Request-ID", "X-Trace-ID", "X-Error-ID"],
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
    error_id = getattr(request.state, "error_id", None)
    if not error_id and exc.status_code >= 500:
        try:
            from app.core.observability.aols import new_error_id

            error_id = new_error_id()
            request.state.error_id = error_id
        except Exception:
            error_id = None
    if exc.status_code >= 500:
        try:
            from app.core.observability.aols import LogEvent, get_logger

            get_logger("app.errors").error(
                str(LogEvent.SYSTEM_ERROR),
                error_type=type(exc).__name__,
                error_message=exc.message,
                status_code=exc.status_code,
                path=request.url.path,
                request_id=rid,
                error_id=error_id,
            )
        except Exception:
            pass
    body = error_response(
        exc.status_code,
        exc.message,
        exc.detail,
        request_id=rid,
        error_id=error_id if exc.status_code >= 500 else None,
    )
    resp = JSONResponse(status_code=exc.status_code, content=body)
    if error_id:
        resp.headers["X-Error-ID"] = str(error_id)
    return resp


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import traceback

    rid = getattr(request.state, "request_id", None)
    try:
        from app.core.observability.aols import LogEvent, get_logger, new_error_id

        error_id = getattr(request.state, "error_id", None) or new_error_id()
        request.state.error_id = error_id
        get_logger("app.errors").error(
            str(LogEvent.SYSTEM_ERROR),
            error_type=type(exc).__name__,
            error_message=str(exc),
            status_code=500,
            path=request.url.path,
            request_id=rid,
            error_id=error_id,
            exc_info=True,
        )
    except Exception:
        error_id = getattr(request.state, "error_id", None)

    stack = traceback.format_exc() if settings.DEBUG else None
    resp = JSONResponse(
        status_code=500,
        content=error_response(
            500,
            "Internal error",
            str(exc) if settings.DEBUG else None,
            request_id=rid,
            stacktrace=stack,
            error_id=error_id,
        ),
    )
    if error_id:
        resp.headers["X-Error-ID"] = str(error_id)
    return resp


# ---- Prometheus metrics ----
@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> Any:
    """Prometheus text exposition endpoint (scraped by Prometheus / Grafana Agent).

    Public path (no API key). Disable via ``METRICS_ENABLED=false`` to return 404.
    """
    if not settings.METRICS_ENABLED:
        return JSONResponse(status_code=404, content={"detail": "Metrics disabled"})
    return get_metrics_response()


# ---- Health checks (liveness / readiness / composite) ----
APP_VERSION = "1.0.0"


async def _probe_services() -> dict[str, str]:
    """Probe database and Redis; return per-service status strings."""
    from sqlalchemy import text
    from app.core.dependencies import engine

    services: dict[str, str] = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"] = "ok"
    except Exception as e:
        services["database"] = f"error: {e}"

    # Lite / eager / memory queue: never block readiness on Redis
    skip_redis = bool(settings.CELERY_TASK_ALWAYS_EAGER)
    try:
        from app.core.profiles import current_profile, get_task_queue

        if current_profile() == "lite" or get_task_queue().is_eager():
            skip_redis = True
        if get_task_queue().backend_name in {"eager", "memory"}:
            skip_redis = True
    except Exception:
        pass

    if skip_redis:
        services["redis"] = "skipped (lite/eager)"
    else:
        try:
            from app.core.dependencies import get_redis

            r = await get_redis()
            await r.ping()
            services["redis"] = "ok"
        except Exception:
            services["redis"] = "unavailable"
    return services


@app.get("/health/live")
async def liveness() -> dict[str, Any]:
    """Kubernetes-style liveness probe — process is up, no dependency checks.

    Always returns HTTP 200 if the event loop can serve the request.
    """
    return {
        "status": "alive",
        "app": settings.APP_NAME,
        "version": APP_VERSION,
    }


@app.get("/health/ready")
async def readiness(request: Request) -> JSONResponse:
    """Kubernetes-style readiness probe — ready to accept traffic.

    Returns 200 when the database is reachable; 503 when critical deps fail.
    Redis is required only when not in Celery eager mode.
    """
    services = await _probe_services()
    critical_ok = services.get("database") == "ok"
    redis_ok = services.get("redis", "").startswith(("ok", "skipped"))
    ready = critical_ok and redis_ok
    deploy = {}
    try:
        from app.core.profiles import profile_status

        deploy = profile_status()
    except Exception:
        pass
    body: dict[str, Any] = {
        "status": "ready" if ready else "not_ready",
        "app": settings.APP_NAME,
        "version": APP_VERSION,
        "services": services,
        "celery_eager": settings.CELERY_TASK_ALWAYS_EAGER,
        "deploy": deploy,
    }
    return JSONResponse(status_code=200 if ready else 503, content=body)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Composite health check with database and Redis connectivity.

    Backward-compatible with existing Docker healthchecks. Prefer
    ``/health/live`` and ``/health/ready`` for orchestrators.
    """
    services = await _probe_services()
    critical_ok = services.get("database") == "ok"
    redis_ok = services.get("redis", "").startswith(("ok", "skipped"))
    all_healthy = critical_ok and redis_ok
    deploy = {}
    try:
        from app.core.profiles import profile_status

        deploy = profile_status()
    except Exception:
        pass
    return {
        "status": "healthy" if all_healthy else "degraded",
        "app": settings.APP_NAME,
        "version": APP_VERSION,
        "services": services,
        "celery_eager": settings.CELERY_TASK_ALWAYS_EAGER,
        "deploy": deploy,
    }

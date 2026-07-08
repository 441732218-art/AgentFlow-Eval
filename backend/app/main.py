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
from app.core.middleware import RequestIDMiddleware

setup_logging()

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    HAS_SLOWAPI = True
except ImportError:
    HAS_SLOWAPI = False


# ---- Lifespan events ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    from app.models.base import Base
    from app.core.dependencies import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    import logging
    logging.getLogger(__name__).info("Tables initialized")
    yield
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

# ---- Request tracing ----
app.add_middleware(RequestIDMiddleware)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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
    try:
        from app.core.dependencies import get_redis
        r = await get_redis()
        await r.ping()
        services["redis"] = "ok"
    except Exception:
        services["redis"] = "unavailable"
    all_healthy = all(v == "ok" for v in services.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "services": services,
    }

# (c) 2026 AgentFlow-Eval
"""Request tracing, security headers, and optional API-key auth middleware."""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.core.security import (
    authenticate_api_key,
    extract_api_key,
    is_public_path,
)
from app.utils.exceptions import error_response

# Prefer AOLS structured logger; fall back to stdlib
try:
    from app.core.observability.aols import (
        LogEvent,
        bind_request_context,
        clear_request_context,
        get_logger,
        new_error_id,
    )

    log = get_logger("app.http")
    HAS_AOLS = True
except Exception:  # pragma: no cover
    import logging

    log = logging.getLogger(__name__)
    HAS_AOLS = False
    LogEvent = None  # type: ignore[misc, assignment]

    def bind_request_context(**kwargs):  # type: ignore[misc]
        return None

    def clear_request_context() -> None:  # type: ignore[misc]
        return None

    def new_error_id() -> str:  # type: ignore[misc]
        return uuid.uuid4().hex[:16]


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or ""
    return ""


def _skip_access_log(path: str) -> bool:
    raw = getattr(settings, "LOG_ACCESS_SKIP_PATHS", "") or ""
    prefixes = [p.strip() for p in raw.split(",") if p.strip()]
    for p in prefixes:
        if path == p or path.startswith(p.rstrip("/") + "/") or path.startswith(p):
            # exact or prefix: /health matches /health and /health/ready
            if path == p or path.startswith(p):
                return True
    return False


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject request/trace IDs, bind AOLS context, emit structured access logs.

    Behaviour:
      1. Reads ``X-Request-ID`` / ``X-Trace-ID`` or generates a UUID.
      2. Sets request.state + contextvars TraceID + structlog bind.
      3. Echoes IDs on response; optional ``X-Error-ID`` when set.
      4. Logs each request as ``http.request`` / ``http.request.failed``.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Trace-ID")
            or str(uuid.uuid4())
        )
        request.state.request_id = request_id
        try:
            from app.core.observability.tracing import set_trace_id

            set_trace_id(request_id)
        except Exception:
            pass

        client_ip = _client_ip(request)
        path = request.url.path
        method = request.method

        bind_request_context(
            request_id=request_id,
            trace_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
        )

        start = time.perf_counter()
        error_id: str | None = None
        status_code = 500
        response: Response | None = None

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            # Let global handlers format body; still log failed request
            error_id = new_error_id()
            request.state.error_id = error_id
            duration_ms = int((time.perf_counter() - start) * 1000)
            if not _skip_access_log(path):
                self._emit_access(
                    method=method,
                    path=path,
                    status_code=500,
                    latency_ms=duration_ms,
                    request_id=request_id,
                    client_ip=client_ip,
                    error_id=error_id,
                    failed=True,
                )
            clear_request_context()
            raise

        # Actor may be set by auth middleware (inner)
        actor = getattr(request.state, "actor", None)
        if actor:
            bind_request_context(actor=str(actor))

        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = request_id
        err_state = getattr(request.state, "error_id", None)
        if err_state:
            response.headers["X-Error-ID"] = str(err_state)
            error_id = str(err_state)

        failed = status_code >= 400
        if not _skip_access_log(path):
            self._emit_access(
                method=method,
                path=path,
                status_code=status_code,
                latency_ms=duration_ms,
                request_id=request_id,
                client_ip=client_ip,
                actor=str(actor) if actor else None,
                error_id=error_id,
                failed=failed,
            )

        clear_request_context()
        return response

    @staticmethod
    def _emit_access(
        *,
        method: str,
        path: str,
        status_code: int,
        latency_ms: int,
        request_id: str,
        client_ip: str,
        actor: str | None = None,
        error_id: str | None = None,
        failed: bool = False,
    ) -> None:
        event = (
            str(LogEvent.HTTP_REQUEST_FAILED)
            if failed and LogEvent is not None
            else (str(LogEvent.HTTP_REQUEST) if LogEvent is not None else "http.request")
        )
        if failed and LogEvent is None:
            event = "http.request.failed"

        fields: dict = {
            "event": event,
            "method": method,
            "path": path,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "request_id": request_id,
            "trace_id": request_id,
            "client_ip": client_ip,
        }
        if actor:
            fields["actor"] = actor
        if error_id:
            fields["error_id"] = error_id

        try:
            if failed:
                log.warning(event, **{k: v for k, v in fields.items() if k != "event"})
            else:
                log.info(event, **{k: v for k, v in fields.items() if k != "event"})
        except TypeError:
            # stdlib fallback
            log.info(
                "%s %s -> %s [%dms] request_id=%s",
                method,
                path,
                status_code,
                latency_ms,
                request_id,
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach enterprise security response headers to every response."""

    _API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    _DOCS_CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://cdn.jsdelivr.net data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        response.headers.setdefault("X-XSS-Protection", "0")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")

        path = request.url.path
        if path in {"/docs", "/redoc", "/openapi.json"} or path.startswith("/docs"):
            response.headers.setdefault("Content-Security-Policy", self._DOCS_CSP)
        else:
            response.headers.setdefault("Content-Security-Policy", self._API_CSP)

        if settings.is_prod and not settings.DEBUG:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Enforce API key auth for /api/v1 when AUTH_ENABLED=true."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if not settings.AUTH_ENABLED:
            from app.core.rbac import Role

            request.state.actor = "anonymous"
            request.state.role = Role.SYSTEM_ADMIN
            return await call_next(request)

        if is_public_path(path) or not path.startswith("/api/"):
            from app.core.rbac import Role

            request.state.actor = "public"
            request.state.role = Role.VIEWER
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        api_key = extract_api_key(request)
        identity = authenticate_api_key(api_key)
        if identity is None:
            rid = getattr(request.state, "request_id", None)
            return JSONResponse(
                status_code=401,
                content=error_response(
                    401,
                    "Unauthorized",
                    "Provide a valid X-API-Key or Authorization: Bearer <key>",
                    request_id=rid,
                ),
            )

        request.state.actor = identity.actor
        request.state.auth = identity
        request.state.role = identity.role
        return await call_next(request)

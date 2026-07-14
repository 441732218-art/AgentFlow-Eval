# (c) 2026 AgentFlow-Eval
"""Request tracing and optional API-key auth middleware."""

import logging
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.core.security import AUTH_PUBLIC_PATHS, authenticate_api_key, extract_api_key
from app.utils.exceptions import error_response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
      1. Reads X-Request-ID from request headers or generates a UUID.
      2. Injects request_id into the request state for logging.
      3. Adds X-Request-ID to the response headers.
      4. Logs each request with method, path, status, and duration.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = datetime.now(timezone.utc)

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        logger.info(
            "%s %s -> %s [%dms] request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )

        return response


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Enforce API key auth for /api/v1 when AUTH_ENABLED=true."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if not settings.AUTH_ENABLED:
            request.state.actor = "anonymous"
            return await call_next(request)

        if path in AUTH_PUBLIC_PATHS or not path.startswith("/api/"):
            request.state.actor = "public"
            return await call_next(request)

        # CORS preflight
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
        return await call_next(request)

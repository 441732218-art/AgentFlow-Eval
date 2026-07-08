# (c) 2026 AgentFlow-Eval
"""Request tracing middleware - injects X-Request-ID into every request."""

import logging
import uuid
from datetime import datetime, timezone

from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

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

# (c) 2026 AgentFlow-Eval
"""Custom exception hierarchy and unified error response format."""

from __future__ import annotations
from typing import Any
from datetime import datetime, timezone


class AgentFlowError(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str = "Internal error", status_code: int = 500, detail: Any = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


class NotFoundError(AgentFlowError):
    """Resource not found (HTTP 404)."""
    def __init__(self, resource: str = "Resource", resource_id: str = ""):
        msg = f"{resource} not found: {resource_id}" if resource_id else f"{resource} not found"
        super().__init__(message=msg, status_code=404)


class ValidationError(AgentFlowError):
    """Request validation failed (HTTP 422)."""
    def __init__(self, message: str = "Validation failed", detail: Any = None):
        super().__init__(message=message, status_code=422, detail=detail)


class BusinessError(AgentFlowError):
    """Business logic error (HTTP 400)."""
    def __init__(self, message: str = "Business error", detail: Any = None):
        super().__init__(message=message, status_code=400, detail=detail)


class TaskStateError(AgentFlowError):
    """Task state conflict (HTTP 409)."""
    def __init__(self, message: str = "Task state error"):
        super().__init__(message=message, status_code=409)


class ExternalServiceError(AgentFlowError):
    """External service unavailable (HTTP 503)."""
    def __init__(self, message: str = "External service error", detail: Any = None):
        super().__init__(message=message, status_code=503, detail=detail)


class RateLimitError(AgentFlowError):
    """Rate limit exceeded (HTTP 429)."""
    def __init__(self, message: str = "Too many requests", detail: Any = None):
        super().__init__(message=message, status_code=429, detail=detail)


class ForbiddenError(AgentFlowError):
    """Permission denied (HTTP 403)."""

    def __init__(self, message: str = "Forbidden", detail: Any = None):
        super().__init__(message=message, status_code=403, detail=detail)


def error_response(
    status_code: int,
    message: str,
    detail: Any = None,
    request_id: str | None = None,
    stacktrace: str | None = None,
    error_id: str | None = None,
) -> dict[str, Any]:
    """Generate unified JSON error response.

    Returns dict with code, message, detail, timestamp, request_id,
    optional error_id (support correlation), and stacktrace (dev only).
    """
    resp: dict[str, Any] = {
        "error": {
            "code": status_code,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }
    if detail:
        resp["error"]["detail"] = detail
    if request_id:
        resp["error"]["request_id"] = request_id
    if error_id:
        resp["error"]["error_id"] = error_id
    if stacktrace:
        resp["error"]["stacktrace"] = stacktrace
    return resp

# (c) 2026 AgentFlow-Eval
"""Request / agent context binding for structured logs (structlog contextvars)."""

from __future__ import annotations

import uuid
from typing import Any

try:
    from structlog.contextvars import (  # type: ignore[import-untyped]
        bind_contextvars,
        clear_contextvars,
        get_contextvars,
    )

    HAS_STRUCTLOG = True
except ImportError:  # pragma: no cover
    HAS_STRUCTLOG = False

    def bind_contextvars(**kwargs: Any) -> None:  # type: ignore[misc]
        return None

    def clear_contextvars() -> None:  # type: ignore[misc]
        return None

    def get_contextvars() -> dict[str, Any]:  # type: ignore[misc]
        return {}


def new_error_id() -> str:
    """Opaque error id for client-facing correlation (short uuid4 hex)."""
    return uuid.uuid4().hex[:16]


def bind_request_context(
    *,
    request_id: str | None = None,
    trace_id: str | None = None,
    actor: str | None = None,
    method: str | None = None,
    path: str | None = None,
    client_ip: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Bind HTTP-scoped fields into structlog contextvars."""
    payload: dict[str, Any] = {}
    if request_id:
        payload["request_id"] = request_id
    if trace_id:
        payload["trace_id"] = trace_id
    if actor:
        payload["actor"] = actor
    if method:
        payload["method"] = method
    if path:
        payload["path"] = path
    if client_ip:
        payload["client_ip"] = client_ip
    if extra:
        payload.update(extra)
    if payload:
        bind_contextvars(**payload)


def clear_request_context() -> None:
    """Clear all structlog contextvars (end of request / task)."""
    clear_contextvars()


def get_bound_context() -> dict[str, Any]:
    """Snapshot of current bound contextvars."""
    try:
        return dict(get_contextvars())
    except Exception:
        return {}


def bind_agent_context(
    *,
    task_id: str | None = None,
    agent_id: str | None = None,
    agent_version: str | None = None,
    execution_id: str | None = None,
) -> None:
    """Bind agent_context nested fields for Phase 3 runners."""
    agent_context: dict[str, Any] = {}
    if agent_id:
        agent_context["agent_id"] = agent_id
    if agent_version:
        agent_context["agent_version"] = agent_version
    if execution_id:
        agent_context["execution_id"] = execution_id
    if task_id:
        agent_context["task_id"] = task_id
        bind_contextvars(task_id=task_id)
    if agent_context:
        bind_contextvars(agent_context=agent_context)


def bind_step_context(
    *,
    step_id: str | None = None,
    step_type: str | None = None,
    step_index: int | None = None,
) -> None:
    """Bind step_context for Agent step logs (Phase 3)."""
    step: dict[str, Any] = {}
    if step_id:
        step["step_id"] = step_id
    if step_type:
        step["step_type"] = step_type
    if step_index is not None:
        step["step_index"] = step_index
    if step:
        bind_contextvars(step_context=step)

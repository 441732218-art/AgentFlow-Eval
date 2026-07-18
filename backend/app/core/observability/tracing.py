# (c) 2026 AgentFlow-Eval
"""Request / job TraceID via contextvars (full-chain correlation)."""

from __future__ import annotations

import contextvars
import uuid
from typing import Any

_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "agentflow_trace_id", default=""
)


def get_trace_id() -> str:
    return _trace_id.get() or ""


def set_trace_id(trace_id: str | None) -> contextvars.Token[str]:
    tid = (trace_id or "").strip() or new_trace_id()
    return _trace_id.set(tid)


def clear_trace_id(token: contextvars.Token[str] | None = None) -> None:
    if token is not None:
        try:
            _trace_id.reset(token)
            return
        except Exception:
            pass
    _trace_id.set("")


def new_trace_id() -> str:
    return uuid.uuid4().hex


def ensure_trace_id(existing: str | None = None) -> str:
    """Return current trace id or set from existing / generate new."""
    cur = get_trace_id()
    if cur:
        return cur
    tid = (existing or "").strip() or new_trace_id()
    set_trace_id(tid)
    return tid


def trace_headers() -> dict[str, str]:
    tid = get_trace_id()
    return {"X-Request-ID": tid, "X-Trace-ID": tid} if tid else {}


def bind_from_mapping(data: dict[str, Any] | None) -> str:
    """Restore trace id from task kwargs / event payload (force overwrite)."""
    if not data:
        return ensure_trace_id()
    tid = (
        data.get("_trace_id")
        or data.get("trace_id")
        or data.get("request_id")
        or ""
    )
    if tid:
        set_trace_id(str(tid))
        return str(tid)
    return ensure_trace_id()

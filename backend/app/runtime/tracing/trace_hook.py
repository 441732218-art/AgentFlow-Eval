# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime execution tracing (in-memory; not v1 evaluation trace)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.runtime.context import RuntimeContext
from app.runtime.pipeline.hooks import ExecutionHook
from app.runtime.tracing.events import TraceEvent

RUNTIME_TRACE_KEY = "runtime_trace"


def ensure_runtime_trace(context: RuntimeContext) -> dict[str, Any]:
    """Return the runtime trace bucket on context metadata, creating if needed."""
    trace = context.metadata.get(RUNTIME_TRACE_KEY)
    if not isinstance(trace, dict):
        trace = {}
        context.metadata[RUNTIME_TRACE_KEY] = trace
    trace.setdefault("events", [])
    return trace


def append_trace_event(context: RuntimeContext, event: TraceEvent) -> None:
    """Append a serialized trace event without overwriting existing metadata."""
    trace = ensure_runtime_trace(context)
    events = trace.setdefault("events", [])
    events.append(event.to_dict())


class TraceHook(ExecutionHook):
    """Records Runtime pipeline lifecycle events on ``context.metadata``."""

    def before_execute(self, context: RuntimeContext, task: str) -> None:
        append_trace_event(
            context,
            TraceEvent(
                event_type="execution.started",
                timestamp=datetime.now(timezone.utc),
                metadata={"task": task},
            ),
        )

    def after_execute(self, context: RuntimeContext, result: Any) -> None:
        append_trace_event(
            context,
            TraceEvent(
                event_type="execution.completed",
                timestamp=datetime.now(timezone.utc),
                metadata={"output": result},
            ),
        )

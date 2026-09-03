# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime correlation attachment helpers."""

from __future__ import annotations

from app.runtime.context import RuntimeContext
from app.runtime.correlation.models import CorrelationContext

CORRELATION_CONTEXT_METADATA_KEY = "runtime_correlation_context"


def attach_correlation_context(
    runtime_context: RuntimeContext,
    correlation: CorrelationContext,
) -> RuntimeContext:
    """Attach an active correlation context to runtime metadata."""
    runtime_context.metadata[CORRELATION_CONTEXT_METADATA_KEY] = correlation
    return runtime_context


def get_correlation_context(runtime_context: RuntimeContext) -> CorrelationContext | None:
    """Return the active correlation context from runtime metadata, if present."""
    value = runtime_context.metadata.get(CORRELATION_CONTEXT_METADATA_KEY)
    if value is None:
        return None
    if not isinstance(value, CorrelationContext):
        raise TypeError(
            "context.metadata.runtime_correlation_context must be a CorrelationContext instance"
        )
    return value

# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime context aggregation and pipeline execution context."""

from __future__ import annotations

from app.runtime.context.pipeline_context import RuntimeContext

__all__ = [
    "AggregatedRuntimeContext",
    "RuntimeContext",
    "RuntimeContextManager",
    "RuntimeContextSnapshot",
    "build_snapshot",
]


def __getattr__(name: str):
    if name == "AggregatedRuntimeContext":
        from app.runtime.context.models import RuntimeContext as AggregatedRuntimeContext

        return AggregatedRuntimeContext
    if name == "RuntimeContextManager":
        from app.runtime.context.manager import RuntimeContextManager

        return RuntimeContextManager
    if name == "RuntimeContextSnapshot":
        from app.runtime.context.snapshot import RuntimeContextSnapshot

        return RuntimeContextSnapshot
    if name == "build_snapshot":
        from app.runtime.context.snapshot import build_snapshot

        return build_snapshot
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

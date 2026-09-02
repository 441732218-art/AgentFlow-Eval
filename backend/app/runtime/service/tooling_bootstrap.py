# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Production tooling bootstrap — wires Application providers into Runtime registries."""

from __future__ import annotations

from app.applications.bootstrap import bootstrap_applications
from app.runtime.tools.factory import create_tool_execution_engine
from app.runtime.tools.registry import (
    get_local_handler_registry,
    get_tool_registry,
    reset_tool_registry,
)
from app.runtime.executor import AgentExecutor
from app.runtime.pipeline import ExecutionPipeline
from app.runtime.tracing import TraceHook

_production_tooling_bootstrapped = False


def bootstrap_production_tooling() -> None:
    """Load Runtime tool registries and application providers once per process.

    Idempotent: safe to call from every ``RuntimeService`` construction.
    Application registration uses explicit registries — no hidden globals in
    ``applications.bootstrap``.
    """
    global _production_tooling_bootstrapped
    if _production_tooling_bootstrapped:
        return

    registry = get_tool_registry()
    handler_registry = get_local_handler_registry()
    bootstrap_applications(registry, handler_registry)
    _production_tooling_bootstrapped = True


def create_production_executor() -> AgentExecutor:
    """Build the default production ``AgentExecutor`` with tool engine wiring."""
    registry = get_tool_registry()
    handler_registry = get_local_handler_registry()
    engine = create_tool_execution_engine(handler_registry=handler_registry)
    pipeline = ExecutionPipeline(
        hooks=[TraceHook()],
        tool_execution_engine=engine,
    )
    return AgentExecutor(tool_registry=registry, pipeline=pipeline)


def is_production_tooling_bootstrapped() -> bool:
    """Return whether application providers have been loaded (test helper)."""
    return _production_tooling_bootstrapped


def reset_production_tooling() -> None:
    """Reset bootstrap state and registry singletons (test isolation only)."""
    global _production_tooling_bootstrapped
    _production_tooling_bootstrapped = False
    reset_tool_registry()

# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance middleware helpers for runtime tool execution."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.executor.execution_context import ExecutionContext


def use_governance_lifecycle(context: ExecutionContext | None) -> bool:
    """Return True when unified governance lifecycle should orchestrate execution."""
    return context is not None and context.governance_lifecycle is not None

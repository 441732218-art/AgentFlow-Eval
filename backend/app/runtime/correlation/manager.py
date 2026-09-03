# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime correlation tree manager."""

from __future__ import annotations

import uuid

from app.runtime.correlation.models import CorrelationContext


class RuntimeCorrelationManager:
    """Maintains runtime correlation trees for executions, steps, and tools."""

    def __init__(self) -> None:
        self._contexts: dict[str, CorrelationContext] = {}
        self._execution_roots: dict[str, str] = {}

    def create_execution_context(self, execution_id: str) -> CorrelationContext:
        """Create the root correlation context for an execution."""
        span_id = uuid.uuid4().hex
        context = CorrelationContext(
            correlation_id=span_id,
            execution_id=execution_id,
            parent_id=None,
            span_id=span_id,
        )
        self._contexts[span_id] = context
        self._execution_roots[execution_id] = span_id
        return context

    def create_child_context(self, parent: CorrelationContext) -> CorrelationContext:
        """Create a child correlation context linked to ``parent``."""
        span_id = uuid.uuid4().hex
        child = CorrelationContext(
            correlation_id=parent.correlation_id,
            execution_id=parent.execution_id,
            parent_id=parent.span_id,
            span_id=span_id,
        )
        self._contexts[span_id] = child
        return child

    def get_context(self, span_id: str) -> CorrelationContext | None:
        return self._contexts.get(span_id)

    def close_context(self, span_id: str) -> None:
        context = self._contexts.pop(span_id, None)
        if context is None:
            return
        root_span_id = self._execution_roots.get(context.execution_id)
        if root_span_id == span_id:
            self._execution_roots.pop(context.execution_id, None)

# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Planner interface for agent execution planning."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.runtime.planning.models import ExecutionPlan

if TYPE_CHECKING:
    from app.runtime.agent.models import AgentDefinition
    from app.runtime.executor.execution_context import ExecutionContext


@runtime_checkable
class Planner(Protocol):
    """Creates an execution plan for an agent task."""

    def create_plan(
        self,
        agent_definition: AgentDefinition,
        task: str,
        context: ExecutionContext,
    ) -> ExecutionPlan:
        """Return an execution plan for the requested agent task."""

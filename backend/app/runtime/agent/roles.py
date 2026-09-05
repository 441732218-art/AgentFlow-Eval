# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent role helpers for runtime policy evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.agent.models import AgentDefinition
    from app.runtime.executor.execution_context import ExecutionContext

# Canonical metadata key populated from ``AgentDefinition.roles`` at execute time.
AGENT_ROLES_METADATA_KEY = "agent_roles"


def attach_agent_roles(
    execution_context: ExecutionContext,
    agent_definition: AgentDefinition,
) -> None:
    """Copy agent-instance roles into ``ExecutionContext.metadata`` for policy checks."""
    if not agent_definition.roles:
        return
    execution_context.metadata[AGENT_ROLES_METADATA_KEY] = list(agent_definition.roles)

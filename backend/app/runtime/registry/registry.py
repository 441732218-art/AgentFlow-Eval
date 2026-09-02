# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent registry interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.registry.models import AgentDefinition


class AgentNotFoundError(LookupError):
    """Raised when an agent identifier is not registered."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agent not found: {agent_id}")


class AgentRegistry(Protocol):
    """Runtime agent definition registry."""

    def register(self, agent: AgentDefinition) -> None:
        """Register or replace an agent definition."""

    def get(self, agent_id: str) -> AgentDefinition | None:
        """Return an agent definition by id, if registered."""

    def list(self) -> list[AgentDefinition]:
        """Return all registered agent definitions."""

    def remove(self, agent_id: str) -> None:
        """Remove an agent definition by id."""

# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory agent registry implementation."""

from __future__ import annotations

import threading

from app.runtime.registry.models import AgentDefinition


class InMemoryAgentRegistry:
    """Thread-safe in-memory agent registry."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}
        self._lock = threading.Lock()

    def register(self, agent: AgentDefinition) -> None:
        with self._lock:
            self._agents[agent.id] = agent

    def get(self, agent_id: str) -> AgentDefinition | None:
        with self._lock:
            agent = self._agents.get(agent_id)
            return agent

    def list(self) -> list[AgentDefinition]:
        with self._lock:
            return list(self._agents.values())

    def remove(self, agent_id: str) -> None:
        with self._lock:
            self._agents.pop(agent_id, None)

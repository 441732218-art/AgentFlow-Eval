# AgentFlow Intelligence v2.0 — Agent Runtime MVP (Sprint 1)
"""In-memory Agent registry: register / get / list. No database."""

from __future__ import annotations

from threading import Lock

from app.core.runtime.agent import Agent
from app.core.runtime.exceptions import AgentNotFoundError, DuplicateAgentError


class AgentRegistry:
    """Process-local store. Not durable; not shared across workers."""

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}
        self._lock = Lock()

    def register(self, agent: Agent) -> Agent:
        """Insert ``agent``. Raises :class:`DuplicateAgentError` on id clash."""
        if not isinstance(agent, Agent):
            raise TypeError("register() expects an Agent")
        agent_id = str(agent.agent_id or "").strip()
        if not agent_id:
            raise ValueError("agent_id is required")
        with self._lock:
            if agent_id in self._agents:
                raise DuplicateAgentError(agent_id)
            self._agents[agent_id] = agent
        return agent

    def get(self, agent_id: str) -> Agent:
        """Return a registered agent or raise :class:`AgentNotFoundError`."""
        key = str(agent_id or "").strip()
        with self._lock:
            agent = self._agents.get(key)
        if agent is None:
            raise AgentNotFoundError(key)
        return agent

    def list(self) -> list[Agent]:
        """Return agents in insertion order (snapshot)."""
        with self._lock:
            return list(self._agents.values())


_REGISTRY: AgentRegistry | None = None
_REGISTRY_LOCK = Lock()


def get_agent_registry() -> AgentRegistry:
    """Process singleton used by the Runtime API."""
    global _REGISTRY
    if _REGISTRY is None:
        with _REGISTRY_LOCK:
            if _REGISTRY is None:
                _REGISTRY = AgentRegistry()
    return _REGISTRY


def reset_agent_registry() -> AgentRegistry:
    """Replace the singleton (tests only). Does not touch v1 tables."""
    global _REGISTRY
    with _REGISTRY_LOCK:
        _REGISTRY = AgentRegistry()
        return _REGISTRY

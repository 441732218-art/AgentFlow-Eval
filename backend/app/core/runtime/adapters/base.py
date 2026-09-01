# AgentFlow Intelligence v2.0 — Agent Runtime MVP (Sprint 1)
"""Adapter contract. Implementations must call build_agent_runner, not LLM APIs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.runtime.agent import Agent
from app.core.runtime.session import AgentSession
from app.core.runtime.state import AgentState

OPENAI_RUNNER_TYPES = frozenset({"", "openai", "react"})
HTTP_RUNNER_TYPES = frozenset({"http", "http_agent", "remote", "webhook"})


class RuntimeAdapter(ABC):
    """Convert Runtime I/O and invoke a v1 runner via ``build_agent_runner``."""

    @abstractmethod
    async def execute(
        self,
        agent: Agent,
        query: str,
        *,
        context: dict[str, Any] | None = None,
        session: AgentSession,
        state: AgentState,
    ) -> dict[str, Any]:
        """Return a v1 pipeline dict (steps / status / final_answer / ...)."""

    def merge_runner_config(
        self,
        agent: Agent,
        *,
        runner_override: str | None = None,
    ) -> dict[str, Any]:
        """Build ``agent_config`` for the v1 factory. Does not mutate ``agent``."""
        cfg = dict(agent.config or {})
        if runner_override:
            cfg["runner"] = runner_override
        elif agent.runner_type and "runner" not in cfg:
            cfg["runner"] = agent.runner_type
        return cfg

    async def invoke_existing_runner(
        self,
        agent: Agent,
        query: str,
        context: dict[str, Any] | None = None,
        *,
        runner_override: str | None = None,
    ) -> dict[str, Any]:
        """Call v1 ``build_agent_runner`` then ``runner.run`` — no LLM client here."""
        from app.core.agent_runner.base import ensure_pipeline_result
        from app.core.agent_runner.factory import build_agent_runner

        cfg = self.merge_runner_config(agent, runner_override=runner_override)
        runner = build_agent_runner(cfg)
        tools = None
        if isinstance(context, dict):
            tools = context.get("tools")
        raw = await runner.run(query, tools=tools, agent_config=cfg)
        return ensure_pipeline_result(raw)

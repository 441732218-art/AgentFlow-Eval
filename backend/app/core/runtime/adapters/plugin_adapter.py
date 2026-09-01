# AgentFlow Intelligence v2.0 — Agent Runtime MVP (Sprint 1)
"""Plugin adapter — wraps plugin runners via build_agent_runner."""

from __future__ import annotations

from typing import Any

from app.core.runtime.adapters.base import RuntimeAdapter
from app.core.runtime.agent import Agent
from app.core.runtime.exceptions import AdapterNotConfiguredError
from app.core.runtime.session import AgentSession
from app.core.runtime.state import AgentState


class PluginAdapter(RuntimeAdapter):
    """Uses the existing plugin capability registry + factory. Does not load plugins."""

    async def execute(
        self,
        agent: Agent,
        query: str,
        *,
        context: dict[str, Any] | None = None,
        session: AgentSession,
        state: AgentState,
    ) -> dict[str, Any]:
        _ = session, state
        runner_type = str(agent.runner_type or "").strip().lower()
        if not runner_type:
            raise AdapterNotConfiguredError(runner_type)
        self._require_plugin_runner(runner_type)
        return await self.invoke_existing_runner(
            agent,
            query,
            context,
            runner_override=runner_type,
        )

    @staticmethod
    def _require_plugin_runner(runner_type: str) -> None:
        """Fail closed if the key is not a registered plugin runner.

        Avoids ``build_agent_runner`` silently falling back to OpenAIReActRunner.
        """
        from app.core.plugins.registry import get_capability_registry

        factory = get_capability_registry().get_runner_factory(runner_type)
        if factory is None:
            raise AdapterNotConfiguredError(runner_type)

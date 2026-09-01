# AgentFlow Intelligence v2.0 — Agent Runtime MVP (Sprint 1)
"""HTTP adapter — wraps existing HttpAgentRunner via build_agent_runner."""

from __future__ import annotations

from typing import Any

from app.core.runtime.adapters.base import RuntimeAdapter
from app.core.runtime.agent import Agent
from app.core.runtime.session import AgentSession
from app.core.runtime.state import AgentState


class HttpAdapter(RuntimeAdapter):
    """Factory selects HttpAgentRunner when ``runner=http``. No new HTTP client here."""

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
        return await self.invoke_existing_runner(
            agent,
            query,
            context,
            runner_override="http",
        )

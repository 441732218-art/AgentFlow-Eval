# AgentFlow Intelligence v2.0 — Agent Runtime MVP (Sprint 1)
"""AgentExecutor: Runtime → Adapter → existing v1 runner (via factory).

This module does not call LLM APIs. Adapter implementations (Step 4) must
invoke ``build_agent_runner``; this file only resolves and awaits an adapter.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.core.runtime.adapters.base import RuntimeAdapter
from app.core.runtime.agent import Agent
from app.core.runtime.session import AgentSession
from app.core.runtime.state import AgentState


class AdapterResolver(Protocol):
    def __call__(self, runner_type: str) -> RuntimeAdapter: ...


def _default_adapter_resolver(runner_type: str) -> RuntimeAdapter:
    from app.core.runtime.adapters import resolve_adapter

    return resolve_adapter(runner_type)


def _query_from_input(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


class AgentExecutor:
    """Orchestrates one synchronous Runtime run (no Celery).

    ``adapter_resolver`` is injected so Step 3 can be tested without
    implementing OpenAI/HTTP/plugin adapters. Step 4 will supply the
    default resolver that wraps ``build_agent_runner``.
    """

    def __init__(self, adapter_resolver: AdapterResolver | None = None) -> None:
        self._adapter_resolver = adapter_resolver or _default_adapter_resolver

    def resolve_adapter(self, runner_type: str) -> RuntimeAdapter:
        return self._adapter_resolver(str(runner_type or "").strip())

    async def execute(
        self,
        agent: Agent,
        input: Any,
        context: dict[str, Any] | None,
        *,
        session: AgentSession,
        state: AgentState,
    ) -> dict[str, Any]:
        """Run: session running → adapter → apply result → session done."""
        session.mark_running()
        state.status = "running"
        state.input = input
        state.context = dict(context or {})

        query = _query_from_input(input)
        try:
            adapter = self.resolve_adapter(agent.runner_type)
            raw = await adapter.execute(
                agent,
                query,
                context=state.context,
                session=session,
                state=state,
            )
        except Exception as exc:
            session.mark_failed(str(exc))
            state.status = "failed"
            state.extra = {**state.extra, "error_message": str(exc)}
            raise

        result = dict(raw or {})
        result.setdefault("steps", [])
        result.setdefault("status", "success")
        result.setdefault("final_answer", result.get("output", ""))
        state.apply_pipeline_result(result)
        if str(result.get("status") or "") == "failed":
            session.mark_failed(str(result.get("error_message") or ""))
        else:
            session.mark_completed()
        return result

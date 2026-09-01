# AgentFlow Intelligence v2.0 — Agent Runtime MVP (Sprint 1)
"""Unified AgentRuntime entry. Delegates to Executor; never calls LLM directly."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.runtime.agent import Agent
from app.core.runtime.executor import AdapterResolver, AgentExecutor
from app.core.runtime.session import AgentSession, new_session_id
from app.core.runtime.state import AgentState


def _bind_trace_id(existing: str | None = None) -> str:
    """Correlation id only — does not insert a v1 ``traces`` row."""
    from app.core.observability.tracing import ensure_trace_id, new_trace_id, set_trace_id

    if existing and str(existing).strip():
        tid = str(existing).strip()
        set_trace_id(tid)
        return tid
    current = ensure_trace_id()
    return current or new_trace_id()


@dataclass
class RuntimeResult:
    """Public result of ``AgentRuntime.run`` (API will map this in Step 5)."""

    agent_id: str
    output: Any
    trace_id: str
    session_id: str
    status: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class AgentRuntime:
    """Process entry: create session/state, then **must** call Executor."""

    def __init__(
        self,
        executor: AgentExecutor | None = None,
        *,
        adapter_resolver: AdapterResolver | None = None,
    ) -> None:
        if executor is not None:
            self.executor = executor
        else:
            self.executor = AgentExecutor(adapter_resolver=adapter_resolver)

    async def run(
        self,
        agent: Agent,
        input: Any,
        context: dict[str, Any] | None = None,
    ) -> RuntimeResult:
        """Execute one agent synchronously through the Executor."""
        if not isinstance(agent, Agent):
            raise TypeError("run() expects an Agent")

        ctx = dict(context or {})
        trace_id = _bind_trace_id(ctx.get("trace_id"))
        session = AgentSession(
            session_id=new_session_id(),
            agent_id=agent.agent_id,
            trace_id=trace_id,
        )
        state = AgentState(input=input, context=ctx)

        pipeline = await self.executor.execute(
            agent,
            input,
            ctx,
            session=session,
            state=state,
        )

        output = state.output
        if output is None:
            output = pipeline.get("final_answer") or pipeline.get("output") or ""

        return RuntimeResult(
            agent_id=agent.agent_id,
            output=output,
            trace_id=session.trace_id,
            session_id=session.session_id,
            status=session.status,
            steps=list(state.steps),
            extra=dict(state.extra),
        )

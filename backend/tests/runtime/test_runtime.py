# AgentFlow Intelligence v2.0 — AgentRuntime / Executor wiring tests

from __future__ import annotations

from typing import Any

import pytest

from app.core.runtime.agent import Agent
from app.core.runtime.exceptions import AdapterNotConfiguredError
from app.core.runtime.executor import AgentExecutor
from app.core.runtime.runtime import AgentRuntime, RuntimeResult
from app.core.runtime.session import AgentSession
from app.core.runtime.state import AgentState


def _agent() -> Agent:
    return Agent(agent_id="ag-rt", name="rt", runner_type="openai", config={})


class _FakeAdapter:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def execute(
        self,
        agent: Agent,
        query: str,
        *,
        context: dict[str, Any] | None = None,
        session: AgentSession,
        state: AgentState,
    ) -> dict[str, Any]:
        self.queries.append(query)
        return {
            "status": "success",
            "final_answer": f"ok:{query}",
            "steps": [{"thought": "fake"}],
            "total_tokens": 2,
            "response_time_ms": 1,
        }


class _SpyExecutor(AgentExecutor):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.execute_calls = 0

    async def execute(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.execute_calls += 1
        return await super().execute(*args, **kwargs)


@pytest.mark.asyncio
async def test_runtime_run_must_go_through_executor() -> None:
    spy = _SpyExecutor(adapter_resolver=lambda _t: _FakeAdapter())
    runtime = AgentRuntime(spy)
    result = await runtime.run(_agent(), "hello", {})
    assert spy.execute_calls == 1
    assert result.output == "ok:hello"


@pytest.mark.asyncio
async def test_runtime_fails_without_adapter() -> None:
    def _no_adapter(runner_type: str) -> Any:
        raise AdapterNotConfiguredError(runner_type)

    runtime = AgentRuntime(adapter_resolver=_no_adapter)
    with pytest.raises(AdapterNotConfiguredError):
        await runtime.run(_agent(), "hello", {})


@pytest.mark.asyncio
async def test_runtime_succeeds_with_fake_adapter() -> None:
    fake = _FakeAdapter()
    runtime = AgentRuntime(adapter_resolver=lambda _t: fake)
    result = await runtime.run(_agent(), "ping", {"trace_id": "fixed-trace"})
    assert fake.queries == ["ping"]
    assert result.output == "ok:ping"
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_runtime_result_fields_complete() -> None:
    runtime = AgentRuntime(adapter_resolver=lambda _t: _FakeAdapter())
    result = await runtime.run(_agent(), "q", {"trace_id": "tid-1"})
    assert isinstance(result, RuntimeResult)
    assert result.agent_id == "ag-rt"
    assert result.output == "ok:q"
    assert result.trace_id == "tid-1"
    assert result.session_id
    assert result.status == "completed"
    assert result.steps == [{"thought": "fake"}]
    assert result.extra.get("total_tokens") == 2
    assert result.extra.get("response_time_ms") == 1


@pytest.mark.asyncio
async def test_runtime_rejects_non_agent() -> None:
    runtime = AgentRuntime(adapter_resolver=lambda _t: _FakeAdapter())
    with pytest.raises(TypeError, match="Agent"):
        await runtime.run({"agent_id": "x"}, "q", {})  # type: ignore[arg-type]

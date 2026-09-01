# AgentFlow Intelligence v2.0 — Adapter tests (mocked runners only, no live LLM)

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.runtime.adapters import resolve_adapter
from app.core.runtime.adapters.http_adapter import HttpAdapter
from app.core.runtime.adapters.openai_adapter import OpenAIAdapter
from app.core.runtime.adapters.plugin_adapter import PluginAdapter
from app.core.runtime.agent import Agent
from app.core.runtime.exceptions import AdapterNotConfiguredError
from app.core.runtime.session import AgentSession
from app.core.runtime.state import AgentState


class FakeRunner:
    def __init__(self, payload: dict | None = None) -> None:
        self.calls: list[tuple] = []
        self._payload = payload or {
            "status": "success",
            "final_answer": "fake-ok",
            "steps": [{"thought": "mocked"}],
            "total_tokens": 3,
        }

    async def run(self, query, tools=None, *, agent_config=None):
        self.calls.append((query, tools, agent_config))
        return dict(self._payload)


def _session(agent_id: str = "ag-1") -> AgentSession:
    return AgentSession(session_id="s1", agent_id=agent_id, trace_id="t1")


@pytest.mark.asyncio
async def test_openai_adapter_uses_build_agent_runner_not_sdk() -> None:
    agent = Agent(
        agent_id="ag-1",
        name="demo",
        runner_type="openai",
        config={"model": "gpt-4o-mini"},
    )
    fake = FakeRunner()
    with patch(
        "app.core.agent_runner.factory.build_agent_runner",
        return_value=fake,
    ) as factory:
        out = await OpenAIAdapter().execute(
            agent, "hello", context={"tools": []}, session=_session(), state=AgentState()
        )
    factory.assert_called_once()
    passed_cfg = factory.call_args[0][0]
    assert passed_cfg["runner"] == "openai"
    assert passed_cfg["model"] == "gpt-4o-mini"
    assert fake.calls[0][0] == "hello"
    assert out["final_answer"] == "fake-ok"
    assert out["status"] == "success"


@pytest.mark.asyncio
async def test_http_adapter_forces_http_runner_key() -> None:
    agent = Agent(
        agent_id="ag-2",
        name="remote",
        runner_type="http",
        config={"endpoint_url": "https://agent.example/run"},
    )
    fake = FakeRunner({"status": "success", "final_answer": "http-ok", "steps": []})
    with patch(
        "app.core.agent_runner.factory.build_agent_runner",
        return_value=fake,
    ) as factory:
        out = await HttpAdapter().execute(
            agent, "ping", context=None, session=_session("ag-2"), state=AgentState()
        )
    assert factory.call_args[0][0]["runner"] == "http"
    assert out["final_answer"] == "http-ok"


@pytest.mark.asyncio
async def test_plugin_adapter_requires_registered_factory() -> None:
    agent = Agent(agent_id="ag-3", name="echo", runner_type="echo", config={})
    with patch(
        "app.core.plugins.registry.get_capability_registry"
    ) as get_reg:
        reg = MagicMock()
        reg.get_runner_factory.return_value = None
        get_reg.return_value = reg
        with pytest.raises(AdapterNotConfiguredError):
            await PluginAdapter().execute(
                agent, "x", context=None, session=_session("ag-3"), state=AgentState()
            )


@pytest.mark.asyncio
async def test_plugin_adapter_invokes_factory_when_registered() -> None:
    agent = Agent(agent_id="ag-4", name="echo", runner_type="echo", config={})
    fake = FakeRunner({"status": "success", "final_answer": "echo-ok", "steps": []})
    plugin_factory = MagicMock()
    with (
        patch("app.core.plugins.registry.get_capability_registry") as get_reg,
        patch(
            "app.core.agent_runner.factory.build_agent_runner",
            return_value=fake,
        ) as factory,
    ):
        reg = MagicMock()
        reg.get_runner_factory.return_value = plugin_factory
        get_reg.return_value = reg
        out = await PluginAdapter().execute(
            agent, "q", context=None, session=_session("ag-4"), state=AgentState()
        )
    factory.assert_called_once()
    assert factory.call_args[0][0]["runner"] == "echo"
    assert out["final_answer"] == "echo-ok"


def test_resolve_adapter_routing() -> None:
    assert isinstance(resolve_adapter("openai"), OpenAIAdapter)
    assert isinstance(resolve_adapter("react"), OpenAIAdapter)
    assert isinstance(resolve_adapter("http"), HttpAdapter)
    assert isinstance(resolve_adapter("webhook"), HttpAdapter)
    assert isinstance(resolve_adapter("echo"), PluginAdapter)


@pytest.mark.asyncio
async def test_executor_default_resolver_uses_openai_adapter() -> None:
    from app.core.runtime.executor import AgentExecutor
    from app.core.runtime.runtime import AgentRuntime

    agent = Agent(agent_id="ag-5", name="r", runner_type="openai", config={})
    fake = FakeRunner({"status": "success", "final_answer": "via-rt", "steps": []})
    with patch(
        "app.core.agent_runner.factory.build_agent_runner",
        return_value=fake,
    ):
        result = await AgentRuntime(AgentExecutor()).run(agent, "in", {})
    assert result.output == "via-rt"
    assert result.trace_id
    assert result.status == "completed"

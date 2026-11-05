# AgentFlow Intelligence v2.0 — Runtime API tests (no live LLM)

from __future__ import annotations

from typing import Any, Callable

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints.runtime import get_runtime, get_runtime_registry
from app.core.runtime.agent import Agent
from app.core.runtime.registry import AgentRegistry
from app.core.runtime.runtime import AgentRuntime
from app.main import app

# Keys this module installs into app.dependency_overrides.
_OVERRIDE_KEYS = (get_runtime_registry, get_runtime)


class _FakeAdapter:
    async def execute(
        self,
        agent: Agent,
        query: str,
        *,
        context: dict[str, Any] | None = None,
        session: Any = None,
        state: Any = None,
    ) -> dict[str, Any]:
        return {
            "status": "success",
            "final_answer": f"mock:{query}",
            "steps": [{"thought": "api-mock"}],
            "total_tokens": 0,
        }


def _snapshot_owned_overrides() -> dict[Callable[..., Any], tuple[bool, Any]]:
    snap: dict[Callable[..., Any], tuple[bool, Any]] = {}
    for key in _OVERRIDE_KEYS:
        if key in app.dependency_overrides:
            snap[key] = (True, app.dependency_overrides[key])
        else:
            snap[key] = (False, None)
    return snap


def _restore_owned_overrides(
    snap: dict[Callable[..., Any], tuple[bool, Any]],
) -> None:
    for key, (had, previous) in snap.items():
        if had:
            app.dependency_overrides[key] = previous
        else:
            app.dependency_overrides.pop(key, None)


@pytest.fixture
async def client():
    snap = _snapshot_owned_overrides()
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        _restore_owned_overrides(snap)


@pytest.mark.asyncio
async def test_runtime_disabled_returns_503(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", False)
    resp = await client.get("/api/v1/runtime/agents")
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"] == "runtime_disabled"
    assert body["message"] == "Agent Runtime v2 is disabled"


@pytest.mark.asyncio
async def test_runtime_disabled_blocks_create_and_run(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", False)
    created = await client.post(
        "/api/v1/runtime/agents",
        json={"name": "x", "runner_type": "openai", "config": {}},
    )
    assert created.status_code == 503
    ran = await client.post("/api/v1/runtime/agents/any/run", json={"input": "hi"})
    assert ran.status_code == 503
    assert ran.json()["error"] == "runtime_disabled"


@pytest.mark.asyncio
async def test_register_and_list_agents(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", True)
    registry = AgentRegistry()
    app.dependency_overrides[get_runtime_registry] = lambda: registry

    created = await client.post(
        "/api/v1/runtime/agents",
        json={
            "name": "demo",
            "runner_type": "openai",
            "config": {"model": "gpt-4o-mini", "api_key": "sk-secret"},
            "agent_id": "ag-demo",
        },
    )
    assert created.status_code == 200
    data = created.json()
    assert data["agent_id"] == "ag-demo"
    assert data["name"] == "demo"
    assert data["runner_type"] == "openai"
    assert data["config"]["model"] == "gpt-4o-mini"
    assert data["config"]["api_key"] == "[REDACTED]"
    assert "adapter" not in data
    assert "runner" not in data

    listed = await client.get("/api/v1/runtime/agents")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert payload["items"][0]["agent_id"] == "ag-demo"


@pytest.mark.asyncio
async def test_run_agent_with_mock_adapter(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", True)
    registry = AgentRegistry()
    runtime = AgentRuntime(adapter_resolver=lambda _t: _FakeAdapter())
    app.dependency_overrides[get_runtime_registry] = lambda: registry
    app.dependency_overrides[get_runtime] = lambda: runtime

    await client.post(
        "/api/v1/runtime/agents",
        json={"name": "r", "runner_type": "openai", "agent_id": "ag-run", "config": {}},
    )
    resp = await client.post(
        "/api/v1/runtime/agents/ag-run/run",
        json={"input": "hello", "context": {}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_id"] == "ag-run"
    assert body["output"] == "mock:hello"
    assert body["trace_id"]
    assert set(body.keys()) == {"agent_id", "output", "trace_id"}


@pytest.mark.asyncio
async def test_run_unknown_agent_404(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", True)
    app.dependency_overrides[get_runtime_registry] = lambda: AgentRegistry()
    resp = await client.post("/api/v1/runtime/agents/missing/run", json={"input": "x"})
    assert resp.status_code == 404
    assert resp.json()["error"] == "agent_not_found"

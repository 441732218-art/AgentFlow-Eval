# AgentFlow Intelligence v2.0 — Runtime API stabilization tests (Phase 7.3)

from __future__ import annotations

import inspect

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints.runtime import get_runtime_service, reset_runtime_service
from app.main import app
from app.runtime.execution import InMemoryExecutionStore
from app.runtime.service.runtime_service import RuntimeService

EXECUTE_ALLOWED_KEYS = frozenset({"execution_id", "status", "output", "error"})
QUERY_ALLOWED_KEYS = frozenset(
    {"execution_id", "status", "output", "error", "created_at", "updated_at"}
)
FORBIDDEN_KEYS = frozenset(
    {
        "agent_id",
        "tool",
        "tool_output",
        "tool_calls",
        "trace_events",
        "runtime_trace",
        "memory_data",
        "trace_reference",
        "knowledge",
        "metadata",
    }
)


@pytest.fixture(autouse=True)
def _reset_runtime_singleton() -> None:
    reset_runtime_service()
    app.dependency_overrides.clear()
    yield
    reset_runtime_service()
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _inject_service() -> RuntimeService:
    store = InMemoryExecutionStore()
    service = RuntimeService(execution_store=store)
    app.dependency_overrides[get_runtime_service] = lambda: service
    return service


@pytest.mark.asyncio
async def test_runtime_api_execute_response_contract_snapshot(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", True)
    _inject_service()

    resp = await client.post(
        "/api/v1/runtime/execute",
        json={"agent_id": "sales-agent", "task": "contract snapshot"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert frozenset(body.keys()) == EXECUTE_ALLOWED_KEYS
    assert FORBIDDEN_KEYS.isdisjoint(body.keys())


@pytest.mark.asyncio
async def test_execution_query_isolation_from_trace_and_memory(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", True)
    _inject_service()

    execute_resp = await client.post(
        "/api/v1/runtime/execute",
        json={
            "agent_id": "sales-agent",
            "task": "isolation check",
            "context": {"memory_key": "session-001"},
        },
    )
    execution_id = execute_resp.json()["execution_id"]

    query_resp = await client.get(f"/api/v1/runtime/executions/{execution_id}")

    assert query_resp.status_code == 200
    body = query_resp.json()
    assert frozenset(body.keys()) == QUERY_ALLOWED_KEYS
    assert FORBIDDEN_KEYS.isdisjoint(body.keys())
    assert "runtime_trace" not in body
    assert "memory_data" not in body


@pytest.mark.asyncio
async def test_feature_flag_isolation_blocks_execute_and_query_without_side_effects(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", False)
    service = _inject_service()

    execute_resp = await client.post(
        "/api/v1/runtime/execute",
        json={"agent_id": "sales-agent", "task": "blocked"},
    )
    query_resp = await client.get("/api/v1/runtime/executions/any-id")

    assert execute_resp.status_code == 503
    assert execute_resp.json()["error"] == "runtime_disabled"
    assert query_resp.status_code == 503
    assert query_resp.json()["error"] == "runtime_disabled"
    assert service.get_execution("any-id") is None
    assert len(service.execution_store._records) == 0


def test_runtime_service_boundary_regression_http_handlers_use_service_only() -> None:
    from app.api.v1.endpoints import runtime as runtime_module

    execute_source = inspect.getsource(runtime_module.runtime_execute)
    query_source = inspect.getsource(runtime_module.runtime_get_execution)

    assert "service.execute" in execute_source
    assert "service.get_execution" in query_source
    assert "AgentExecutor(" not in execute_source
    assert "AgentExecutor(" not in query_source
    assert "ExecutionStore(" not in execute_source
    assert "ExecutionStore(" not in query_source
    assert "MemoryProvider" not in execute_source
    assert "MemoryProvider" not in query_source
    assert "TraceHook" not in execute_source
    assert "TraceHook" not in query_source

    forbidden_direct_imports = (
        "from app.runtime.execution import InMemoryExecutionStore",
    )
    module_source = inspect.getsource(runtime_module)
    for forbidden in forbidden_direct_imports:
        assert forbidden not in module_source

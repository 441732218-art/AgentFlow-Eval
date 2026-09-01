# AgentFlow Intelligence v2.0 — Runtime HTTP API integration tests

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints.runtime import get_runtime_service, reset_runtime_service
from app.main import app
from app.runtime.execution import InMemoryExecutionStore
from app.runtime.executor import AgentExecutor
from app.runtime.pipeline import ExecutionPipeline
from app.runtime.service.runtime_service import RuntimeService

FORBIDDEN_RESPONSE_KEYS = {
    "agent_id",
    "runtime_trace",
    "memory_data",
    "tool_calls",
    "trace_reference",
    "knowledge",
}


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


def _shared_runtime_service(
    executor: AgentExecutor | None = None,
) -> RuntimeService:
    store = InMemoryExecutionStore()
    service = RuntimeService(executor=executor, execution_store=store)
    app.dependency_overrides[get_runtime_service] = lambda: service
    return service


@pytest.mark.asyncio
async def test_feature_flag_off_disables_execute_and_skips_store(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", False)
    service = _shared_runtime_service()

    resp = await client.post(
        "/api/v1/runtime/execute",
        json={"agent_id": "sales-agent", "task": "execute task"},
    )

    assert resp.status_code == 503
    body = resp.json()
    assert body["error"] == "runtime_disabled"
    assert service.get_execution("any-id") is None
    assert service.execution_store.get("any-id") is None


@pytest.mark.asyncio
async def test_execute_success_then_query(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", True)
    _shared_runtime_service()

    execute_resp = await client.post(
        "/api/v1/runtime/execute",
        json={"agent_id": "sales-agent", "task": "execute task"},
    )
    assert execute_resp.status_code == 200
    execute_body = execute_resp.json()
    assert execute_body["status"] == "SUCCESS"
    assert execute_body["output"] == "pipeline execution completed"
    assert execute_body["error"] is None
    assert execute_body["execution_id"]

    query_resp = await client.get(
        f"/api/v1/runtime/executions/{execute_body['execution_id']}",
    )
    assert query_resp.status_code == 200
    query_body = query_resp.json()
    assert query_body["execution_id"] == execute_body["execution_id"]
    assert query_body["status"] == "SUCCESS"
    assert query_body["output"] == "pipeline execution completed"
    assert "created_at" in query_body
    assert "updated_at" in query_body


@pytest.mark.asyncio
async def test_execute_failure_persisted(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", True)
    failing_pipeline = MagicMock(spec=ExecutionPipeline)
    failing_pipeline.run.side_effect = RuntimeError("pipeline failed")
    executor = AgentExecutor(pipeline=failing_pipeline)
    service = _shared_runtime_service(executor=executor)

    resp = await client.post(
        "/api/v1/runtime/execute",
        json={
            "agent_id": "test-agent",
            "task": "failure task",
            "context": {"execution_id": "exec-fail-api"},
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["execution_id"] == "exec-fail-api"
    assert body["status"] == "FAILED"
    assert body["error"] == "pipeline failed"
    assert body["output"] is None

    record = service.get_execution("exec-fail-api")
    assert record is not None
    assert record.status == "FAILED"
    assert record.error == "pipeline failed"


@pytest.mark.asyncio
async def test_query_not_found_returns_404(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", True)
    _shared_runtime_service()

    resp = await client.get("/api/v1/runtime/executions/not-exist")

    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "execution_not_found"


@pytest.mark.asyncio
async def test_response_boundary_excludes_internal_fields(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", True)
    _shared_runtime_service()

    execute_resp = await client.post(
        "/api/v1/runtime/execute",
        json={
            "agent_id": "sales-agent",
            "task": "boundary check",
            "context": {"memory_key": "session-001"},
        },
    )
    assert execute_resp.status_code == 200
    execute_body = execute_resp.json()
    assert FORBIDDEN_RESPONSE_KEYS.isdisjoint(execute_body.keys())

    query_resp = await client.get(
        f"/api/v1/runtime/executions/{execute_body['execution_id']}",
    )
    assert query_resp.status_code == 200
    query_body = query_resp.json()
    assert FORBIDDEN_RESPONSE_KEYS.isdisjoint(query_body.keys())

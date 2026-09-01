# AgentFlow Intelligence v2.0 — HTTP memory integration tests (Phase 8.3.2)

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import runtime as runtime_module
from app.api.v1.endpoints.runtime import reset_runtime_service
from app.main import app
from app.runtime.memory.hook import MEMORY_DATA_KEY, MemoryHook


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


@pytest.mark.asyncio
async def test_http_memory_round_trip_across_two_execute_requests(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", True)

    first_resp = await client.post(
        "/api/v1/runtime/execute",
        json={
            "agent_id": "sales-agent",
            "task": "task1",
            "context": {"memory_key": "session-http-001"},
        },
    )
    assert first_resp.status_code == 200
    first_body = first_resp.json()
    assert first_body["status"] == "SUCCESS"

    memory_reads: list[object | None] = []
    original_before = MemoryHook.before_execute

    def capture_before(
        hook_self: MemoryHook,
        context: object,
        task: str,
    ) -> None:
        original_before(hook_self, context, task)
        if task == "task2":
            memory_reads.append(context.metadata.get(MEMORY_DATA_KEY))  # type: ignore[attr-defined]

    with patch.object(MemoryHook, "before_execute", capture_before):
        second_resp = await client.post(
            "/api/v1/runtime/execute",
            json={
                "agent_id": "sales-agent",
                "task": "task2",
                "context": {"memory_key": "session-http-001"},
            },
        )

    assert second_resp.status_code == 200
    second_body = second_resp.json()
    assert second_body["status"] == "SUCCESS"
    assert len(memory_reads) == 1
    assert memory_reads[0] == "pipeline execution completed"

    service = runtime_module.get_runtime_service()
    provider = service.executor.memory_provider
    assert provider is not None
    assert provider.get("session-http-001") == "pipeline execution completed"


@pytest.mark.asyncio
async def test_feature_flag_off_skips_memory_provider_initialization(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.runtime.settings.ENABLE_RUNTIME_V2", False)

    resp = await client.post(
        "/api/v1/runtime/execute",
        json={
            "agent_id": "sales-agent",
            "task": "blocked task",
            "context": {"memory_key": "session-http-off"},
        },
    )

    assert resp.status_code == 503
    assert resp.json()["error"] == "runtime_disabled"
    assert runtime_module._memory_provider_instance is None

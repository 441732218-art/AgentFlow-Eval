# (c) 2026 AgentFlow-Eval
"""End-to-end tests for AgentFlow-Eval API."""

import pytest
from httpx import AsyncClient


class TestEndToEnd:

    # Health check
    @pytest.mark.asyncio
    async def test_01_health_check(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["app"] == "AgentFlow-Eval"

    # Create task
    @pytest.mark.asyncio
    async def test_02_create_task(self, client: AsyncClient):
        payload = {
            "name": "Customer Support Eval",
            "description": "Evaluate agent performance.",
            "agent_config": {"model": "gpt-4o-mini", "temperature": 0},
        }
        resp = await client.post("/api/v1/tasks", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Customer Support Eval"
        assert data["status"] == "pending"
        assert data["test_suite_count"] == 0
        pytest.task_id = data["id"]

    # List tasks
    @pytest.mark.asyncio
    async def test_03_list_tasks(self, client: AsyncClient):
        resp = await client.get("/api/v1/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    # Get single task
    @pytest.mark.asyncio
    async def test_04_get_task(self, client: AsyncClient):
        task_id = getattr(pytest, "task_id", None)
        assert task_id is not None
        resp = await client.get("/api/v1/tasks/" + task_id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == task_id

    # Batch-create test suites
    @pytest.mark.asyncio
    async def test_05_batch_create_suites(self, client: AsyncClient):
        task_id = getattr(pytest, "task_id", None)
        assert task_id is not None
        suites = [
            {"user_query": "Weather in Beijing?", "expected_output": "Sunny, 25C", "expected_tools": ["get_weather"]},
            {"user_query": "Calculate 15*37", "expected_output": "555", "expected_tools": ["calculator"]},
            {"user_query": "Book flight to Shanghai", "expected_output": "Booked", "expected_tools": ["flight_search"]},
        ]
        resp = await client.post("/api/v1/tasks/" + task_id + "/test-suites", json=suites)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["created"] == 3

    # Verify task suite count
    @pytest.mark.asyncio
    async def test_06_verify_suite_count(self, client: AsyncClient):
        task_id = getattr(pytest, "task_id", None)
        assert task_id is not None
        resp = await client.get("/api/v1/tasks/" + task_id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["test_suite_count"] == 3

    # Delete task
    @pytest.mark.asyncio
    async def test_07_delete_task(self, client: AsyncClient):
        task_id = getattr(pytest, "task_id", None)
        assert task_id is not None
        resp = await client.delete("/api/v1/tasks/" + task_id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id

    # Verify deleted
    @pytest.mark.asyncio
    async def test_08_verify_deleted(self, client: AsyncClient):
        task_id = getattr(pytest, "task_id", None)
        resp = await client.get("/api/v1/tasks/" + task_id)
        assert resp.status_code == 404

    # Create task missing name
    @pytest.mark.asyncio
    async def test_09_missing_name(self, client: AsyncClient):
        resp = await client.post("/api/v1/tasks", json={"description": "no name"})
        assert resp.status_code == 422

    # Non-existent task
    @pytest.mark.asyncio
    async def test_10_nonexistent_task(self, client: AsyncClient):
        resp = await client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    # Empty traces list
    @pytest.mark.asyncio
    async def test_11_empty_traces(self, client: AsyncClient):
        resp = await client.get("/api/v1/traces")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    # Non-existent report
    @pytest.mark.asyncio
    async def test_12_nonexistent_report(self, client: AsyncClient):
        resp = await client.get("/api/v1/reports/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

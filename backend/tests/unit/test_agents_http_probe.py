# (c) 2026 AgentFlow-Eval
"""Tests for HTTP Agent probe API + SSRF on probe path."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestProbeSsrf:
    @pytest.mark.asyncio
    async def test_probe_blocks_localhost(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/agents/http/probe",
            json={"endpoint_url": "http://127.0.0.1:8000/run"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert data["ssrf_blocked"] is True
        assert data["reachable"] is False
        assert "127.0.0.1" in (data.get("error") or "") or "Blocked" in (
            data.get("error") or ""
        )

    @pytest.mark.asyncio
    async def test_probe_blocks_file_scheme(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/agents/http/probe",
            json={"endpoint_url": "file:///etc/passwd"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ssrf_blocked"] is True


class TestProbeSuccess:
    @pytest.mark.asyncio
    async def test_probe_ok_json(self, client: AsyncClient) -> None:
        class _Resp:
            status_code = 200
            text = '{"answer": "pong", "total_tokens": 1}'
            headers = {"content-type": "application/json"}

            def json(self):
                return {"answer": "pong", "total_tokens": 1}

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=_Resp())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.api.v1.endpoints.agents_http.httpx.AsyncClient",
            return_value=mock_client,
        ):
            resp = await client.post(
                "/api/v1/agents/http/probe",
                json={
                    "endpoint_url": "https://agent.example.com/v1/run",
                    "query": "ping",
                    "timeout_sec": 5,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ssrf_blocked"] is False
        assert data["reachable"] is True
        assert data["ok"] is True
        assert data["protocol_compatible"] is True
        assert data["final_answer_preview"] == "pong"
        assert data["latency_ms"] is not None


class TestContract:
    @pytest.mark.asyncio
    async def test_contract(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/agents/http/contract")
        assert resp.status_code == 200
        data = resp.json()
        assert data["protocol_version"] == "agentflow.http.v1"
        assert "request" in data

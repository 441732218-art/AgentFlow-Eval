# (c) 2026 AgentFlow-Eval
"""Unit tests for Prometheus metrics instrumentation."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.observability import metrics as m
from app.main import app


def _sample(name: str) -> str:
    """Render registry and return lines containing metric name."""
    text = m.render_metrics().decode("utf-8")
    return "\n".join(line for line in text.splitlines() if name in line)


class TestPathNormalize:
    def test_uuid_collapsed(self) -> None:
        path = "/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000/execute"
        assert m.normalize_path(path) == "/api/v1/tasks/{id}/execute"

    def test_numeric_id(self) -> None:
        assert m.normalize_path("/api/v1/traces/12345") == "/api/v1/traces/{id}"

    def test_static(self) -> None:
        assert m.normalize_path("/health/live") == "/health/live"


class TestObserveHelpers:
    def test_http_request_increments(self) -> None:
        before = _sample("agentflow_http_requests_total")
        m.observe_http_request(
            method="GET",
            path="/api/v1/tasks",
            status_code=200,
            duration_seconds=0.012,
        )
        after = _sample("agentflow_http_requests_total")
        assert "agentflow_http_requests_total" in after
        assert 'method="GET"' in after
        assert 'path="/api/v1/tasks"' in after
        assert len(after) >= len(before)

    def test_task_created_labels(self) -> None:
        m.observe_task_created(
            tenant="alice",
            agent_config={"model": "gpt-4o-mini", "runner": "openai"},
        )
        text = _sample("agentflow_tasks_created_total")
        assert 'tenant="alice"' in text
        assert 'model="gpt-4o-mini"' in text
        assert 'runner="openai"' in text

    def test_evaluation_and_duration(self) -> None:
        m.observe_evaluation(
            status="completed",
            duration_seconds=1.5,
            tenant="ops",
            agent_config={"model": "gpt-4o", "runner": "http"},
            total_tokens=100,
        )
        assert "agentflow_evaluations_total" in _sample("agentflow_evaluations_total")
        assert "agentflow_evaluation_duration_seconds" in _sample(
            "agentflow_evaluation_duration_seconds"
        )
        assert "agentflow_tokens_total" in _sample("agentflow_tokens_total")

    def test_suite_and_judge(self) -> None:
        m.observe_suite_run(
            status="success",
            duration_seconds=0.5,
            agent_config={"runner": "openai", "model": "m"},
            total_tokens=10,
        )
        m.observe_judge(
            mode="rule_only",
            status="ok",
            duration_seconds=0.2,
            token_cost=5,
        )
        assert "agentflow_suite_runs_total" in _sample("agentflow_suite_runs_total")
        assert "agentflow_judge_evaluations_total" in _sample(
            "agentflow_judge_evaluations_total"
        )

    def test_disabled_noop(self) -> None:
        with patch.object(m, "_metrics_enabled", return_value=False):
            # Should not raise
            m.observe_http_request(
                method="GET", path="/x", status_code=200, duration_seconds=0.01
            )


class TestTrackDuration:
    @pytest.mark.asyncio
    async def test_async_decorator_records(self) -> None:
        @m.track_duration("evaluation")
        async def job() -> dict:
            return {
                "status": "completed",
                "total_tokens": 3,
                "tenant": "t1",
                "agent_config": {"model": "x", "runner": "openai"},
            }

        out = await job()
        assert out["status"] == "completed"
        assert "agentflow_evaluations_total" in _sample("agentflow_evaluations_total")

    @pytest.mark.asyncio
    async def test_async_decorator_error(self) -> None:
        @m.track_duration("judge")
        async def boom() -> dict:
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            await boom()
        text = _sample("agentflow_judge_evaluations_total")
        assert 'status="error"' in text or "agentflow_judge" in text


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics_endpoint_ok(self) -> None:
        m.observe_http_request(
            method="GET",
            path="/health",
            status_code=200,
            duration_seconds=0.001,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/metrics")
        assert r.status_code == 200
        body = r.text
        assert "agentflow_http_requests_total" in body
        assert "# HELP" in body or "agentflow_" in body
        # Prometheus content-type
        assert "text/plain" in r.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_metrics_public_with_auth(self) -> None:
        with patch("app.core.middleware.settings") as s:
            s.AUTH_ENABLED = True
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                r = await client.get("/metrics")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_disabled_404(self) -> None:
        from app import main as main_mod

        with patch.object(main_mod.settings, "METRICS_ENABLED", False):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                r = await client.get("/metrics")
        assert r.status_code == 404


class TestExtractors:
    def test_extract_model_runner(self) -> None:
        assert m.extract_model({"model": "gpt-4o"}) == "gpt-4o"
        assert m.extract_runner({"runner": "HTTP"}) == "http"
        assert m.extract_runner({}) == "openai"

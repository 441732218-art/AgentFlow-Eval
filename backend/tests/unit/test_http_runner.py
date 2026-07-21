# (c) 2026 AgentFlow-Eval
"""Tests for HttpAgentRunner and runner factory."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.agent_runner.factory import build_agent_runner
from app.core.agent_runner.http_runner import HttpAgentRunner


class _Resp:
    def __init__(
        self,
        status_code: int = 200,
        data: object | None = None,
        text: str = "",
        content_type: str = "application/json",
    ) -> None:
        self.status_code = status_code
        self._data = data
        self.text = text if text else ("" if data is None else str(data))
        self.headers = {"content-type": content_type}

    def json(self):
        if isinstance(self._data, Exception):
            raise self._data
        return self._data


def _patch_client(response: _Resp):
    client = AsyncMock()
    client.request = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return patch(
        "app.core.agent_runner.http_runner.httpx.AsyncClient", return_value=client
    )


class TestHttpAgentRunner:
    def test_requires_endpoint(self) -> None:
        with pytest.raises(ValueError, match="endpoint_url"):
            HttpAgentRunner(endpoint_url="")

    @pytest.mark.asyncio
    async def test_short_answer_json(self) -> None:
        runner = HttpAgentRunner("https://agent.example/run", timeout_sec=5)
        with _patch_client(_Resp(data={"answer": "42", "total_tokens": 3})):
            result = await runner.run("what is 6*7?", tools=["calculator"])
        assert result["status"] == "success"
        assert result["final_answer"] == "42"
        assert result["total_tokens"] == 3
        assert result["runner"] == "http"
        assert result["steps"][0]["action"] == "final_answer"

    @pytest.mark.asyncio
    async def test_full_payload(self) -> None:
        runner = HttpAgentRunner("https://agent.example/run")
        payload = {
            "steps": [
                {
                    "iteration": 0,
                    "thought": "calc",
                    "action": "calculator",
                    "action_input": "6*7",
                    "observation": "42",
                    "tokens": 10,
                }
            ],
            "final_answer": "42",
            "status": "success",
            "total_tokens": 10,
            "iterations": 1,
        }
        with _patch_client(_Resp(data=payload)):
            result = await runner.run("q")
        assert result["status"] == "success"
        assert len(result["steps"]) == 1
        assert result["final_answer"] == "42"

    @pytest.mark.asyncio
    async def test_http_error_status(self) -> None:
        runner = HttpAgentRunner("https://agent.example/run")
        with _patch_client(
            _Resp(status_code=502, text="bad gateway", content_type="text/plain")
        ):
            result = await runner.run("q")
        assert result["status"] == "failed"
        assert "502" in result["error_message"]

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        import httpx

        runner = HttpAgentRunner("https://agent.example/run", timeout_sec=0.1)
        client = AsyncMock()
        client.request = AsyncMock(side_effect=httpx.TimeoutException("slow"))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        with patch(
            "app.core.agent_runner.http_runner.httpx.AsyncClient", return_value=client
        ):
            result = await runner.run("q")
        assert result["status"] == "failed"
        assert "timeout" in result["error_message"].lower()

    @pytest.mark.asyncio
    async def test_plain_text(self) -> None:
        runner = HttpAgentRunner("https://agent.example/run")
        with _patch_client(
            _Resp(data=None, text="hello world", content_type="text/plain")
        ):
            result = await runner.run("hi")
        assert result["final_answer"] == "hello world"
        assert result["status"] == "success"

    def test_extract_tool_names(self) -> None:
        names = HttpAgentRunner._extract_tool_names(
            [
                "web_search",
                {"type": "function", "function": {"name": "calculator"}},
                {"name": "mail"},
            ]
        )
        assert names == ["web_search", "calculator", "mail"]


class TestFactory:
    def test_openai_default(self) -> None:
        with patch("app.core.agent_runner.openai_runner.AsyncOpenAI"):
            runner = build_agent_runner({"model": "gpt-4o-mini"})
        from app.core.agent_runner.openai_runner import OpenAIReActRunner

        assert isinstance(runner, OpenAIReActRunner)

    def test_http_runner(self) -> None:
        runner = build_agent_runner(
            {
                "runner": "http",
                "endpoint_url": "https://agent.example/v1",
                "headers": {"Authorization": "Bearer x"},
                "timeout_sec": 12,
            }
        )
        assert isinstance(runner, HttpAgentRunner)
        assert runner.endpoint_url == "https://agent.example/v1"
        assert runner.timeout_sec == 12.0
        assert runner.headers["Authorization"] == "Bearer x"

# (c) 2026 AgentFlow-Eval
"""Unit tests for agentflow.http.v1 protocol + ensure_pipeline_result."""

from __future__ import annotations

from app.core.agent_runner.base import AgentResult, ensure_pipeline_result
from app.core.agent_runner.protocol import (
    PROTOCOL_VERSION,
    build_http_request_payload,
    coerce_http_response,
    extract_tool_names,
    failed_http_result,
    parse_http_body,
)


class TestBuildRequest:
    def test_payload_shape(self) -> None:
        body = build_http_request_payload(
            "hello",
            tools=["calculator", {"name": "web_search"}],
            context={"tenant": "acme"},
            meta={"suite_id": "s1"},
        )
        assert body["protocol_version"] == PROTOCOL_VERSION
        assert body["query"] == "hello"
        assert body["tools"] == ["calculator", "web_search"]
        assert body["context"]["tenant"] == "acme"
        assert body["meta"]["suite_id"] == "s1"


class TestCoerceResponse:
    def test_short_answer(self) -> None:
        out = coerce_http_response({"answer": "42", "total_tokens": 3}, elapsed_ms=10)
        assert out["status"] == "success"
        assert out["final_answer"] == "42"
        assert out["total_tokens"] == 3
        assert out["runner"] == "http"
        assert out["protocol_version"] == PROTOCOL_VERSION
        assert out["steps"][0]["action"] == "final_answer"

    def test_output_key(self) -> None:
        out = coerce_http_response({"output": "ok"}, elapsed_ms=1)
        assert out["final_answer"] == "ok"

    def test_plain_string(self) -> None:
        out = coerce_http_response("hello world", elapsed_ms=1)
        assert out["final_answer"] == "hello world"
        assert out["status"] == "success"

    def test_full_steps(self) -> None:
        out = coerce_http_response(
            {
                "steps": [
                    {
                        "iteration": 0,
                        "thought": "t",
                        "action": "calculator",
                        "action_input": "1+1",
                        "observation": "2",
                        "tokens": 5,
                    }
                ],
                "final_answer": "2",
                "status": "success",
                "total_tokens": 5,
            },
            elapsed_ms=9,
        )
        assert len(out["steps"]) == 1
        assert out["steps"][0]["action"] == "calculator"
        assert out["final_answer"] == "2"

    def test_invalid_type(self) -> None:
        out = coerce_http_response([1, 2, 3], query="q", elapsed_ms=1)
        assert out["status"] == "failed"
        assert "Unexpected" in out["error_message"]

    def test_unknown_status_normalized(self) -> None:
        out = coerce_http_response(
            {"answer": "x", "status": "weird"}, elapsed_ms=1
        )
        assert out["status"] == "success"


class TestParseHttpBody:
    def test_http_error(self) -> None:
        out = parse_http_body(
            status_code=502,
            text="bad gateway",
            content_type="text/plain",
            query="q",
            elapsed_ms=5,
            endpoint="https://x",
        )
        assert out["status"] == "failed"
        assert "502" in out["error_message"]

    def test_json_body(self) -> None:
        out = parse_http_body(
            status_code=200,
            text='{"answer": "yes"}',
            content_type="application/json",
            elapsed_ms=2,
        )
        assert out["final_answer"] == "yes"

    def test_plain_text(self) -> None:
        out = parse_http_body(
            status_code=200,
            text="hello",
            content_type="text/plain",
            elapsed_ms=1,
        )
        assert out["final_answer"] == "hello"


class TestFailedAndTools:
    def test_failed_shape(self) -> None:
        out = failed_http_result(query="q", error="boom", elapsed_ms=3)
        assert out["status"] == "failed"
        assert out["error_message"] == "boom"
        assert out["final_answer"] == ""

    def test_extract_tool_names(self) -> None:
        names = extract_tool_names(
            [
                "web_search",
                {"type": "function", "function": {"name": "calculator"}},
                {"name": "mail"},
            ]
        )
        assert names == ["web_search", "calculator", "mail"]


class TestEnsurePipelineResult:
    def test_from_dict(self) -> None:
        d = ensure_pipeline_result({"status": "success", "steps": []})
        assert d["total_tokens"] == 0
        assert d["status"] == "success"

    def test_from_agent_result(self) -> None:
        ar = AgentResult(
            steps=[{"a": 1}],
            total_tokens=9,
            response_time_ms=12,
            status="success",
            final_answer="ok",
            runner="echo",
        )
        d = ensure_pipeline_result(ar)
        assert d["total_tokens"] == 9
        assert d["final_answer"] == "ok"
        assert d["runner"] == "echo"

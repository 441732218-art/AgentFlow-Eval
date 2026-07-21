# (c) 2026 AgentFlow-Eval
"""HTTP Agent protocol (agentflow.http.v1) — request/response + normalize.

Pure helpers with no network I/O so unit tests can lock the contract without
mocking httpx. Used by :class:`HttpAgentRunner`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

PROTOCOL_VERSION = "agentflow.http.v1"

ALLOWED_STATUSES = frozenset({"success", "failed", "max_iterations_reached"})


class HttpAgentRequestV1(BaseModel):
    """Outbound request body posted to a user-hosted Agent service."""

    protocol_version: str = PROTOCOL_VERSION
    query: str
    tools: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class HttpAgentStepV1(BaseModel):
    """One ReAct-style step in a full HTTP agent response."""

    iteration: int = 0
    thought: str = ""
    action: str = "final_answer"
    action_input: str = ""
    observation: str = ""
    tokens: int = 0


class HttpAgentResponseV1(BaseModel):
    """Canonical full response shape (preferred for third-party agents)."""

    status: str = "success"
    final_answer: str = ""
    steps: list[HttpAgentStepV1] = Field(default_factory=list)
    total_tokens: int = 0
    response_time_ms: int = 0
    error_message: str = ""
    iterations: int = 0


def extract_tool_names(
    tools: list[dict[str, Any]] | list[str] | None,
) -> list[str]:
    """Extract tool names from OpenAI-style tool defs or plain strings."""
    if not tools:
        return []
    names: list[str] = []
    for t in tools:
        if isinstance(t, str):
            names.append(t)
        elif isinstance(t, dict):
            fn = t.get("function") if isinstance(t.get("function"), dict) else t
            name = (fn or {}).get("name") or t.get("name") or ""
            if name:
                names.append(str(name))
    return names


def build_http_request_payload(
    query: str,
    *,
    tools: list[dict[str, Any]] | list[str] | None = None,
    context: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the JSON body sent to an external HTTP agent."""
    req = HttpAgentRequestV1(
        query=query,
        tools=extract_tool_names(tools),
        context=dict(context or {}),
        meta=dict(meta or {}),
    )
    return req.model_dump()


def _synthetic_final_step(final_answer: str, total_tokens: int = 0) -> dict[str, Any]:
    return {
        "iteration": 0,
        "thought": "HTTP agent response",
        "action": "final_answer",
        "action_input": str(final_answer),
        "observation": "",
        "tokens": int(total_tokens or 0),
    }


def coerce_http_response(
    data: Any,
    *,
    query: str = "",
    elapsed_ms: int = 0,
    endpoint: str = "",
) -> dict[str, Any]:
    """Normalize arbitrary HTTP body into a pipeline-compatible result dict.

    Accepts:
      1. Full dict with steps/final_answer/status
      2. Short dict with answer | output | final_answer | result
      3. Plain string body
      4. Non-dict → failed
    """
    if isinstance(data, str):
        data = {"answer": data}
    if not isinstance(data, dict):
        return failed_http_result(
            query=query,
            error=f"Unexpected response type: {type(data).__name__}",
            elapsed_ms=elapsed_ms,
            endpoint=endpoint,
        )

    final_answer = (
        data.get("final_answer")
        or data.get("answer")
        or data.get("output")
        or data.get("result")
        or ""
    )
    if final_answer is not None and not isinstance(final_answer, str):
        final_answer = str(final_answer)

    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        steps = [
            _synthetic_final_step(
                str(final_answer or ""),
                int(data.get("total_tokens") or 0),
            )
        ]
    else:
        # Ensure each step is a plain dict
        steps = [dict(s) if isinstance(s, dict) else {"action_input": str(s)} for s in steps]

    status = str(data.get("status") or ("success" if final_answer else "failed"))
    if status not in ALLOWED_STATUSES:
        status = "success" if final_answer else "failed"

    return {
        "steps": steps,
        "total_tokens": int(data.get("total_tokens") or 0),
        "iterations": int(data.get("iterations") or len(steps)),
        "final_answer": str(final_answer) if final_answer is not None else "",
        "status": status,
        "error_message": str(data.get("error_message") or ""),
        "response_time_ms": int(data.get("response_time_ms") or elapsed_ms),
        "runner": "http",
        "endpoint": endpoint,
        "protocol_version": PROTOCOL_VERSION,
    }


def failed_http_result(
    *,
    query: str,
    error: str,
    elapsed_ms: int,
    endpoint: str = "",
) -> dict[str, Any]:
    """Standard failed result for timeouts / HTTP errors / bad payloads."""
    return {
        "steps": [
            {
                "iteration": 0,
                "thought": f"HTTP agent failed for query: {query[:80]}",
                "action": "final_answer",
                "action_input": "",
                "observation": error,
                "tokens": 0,
            }
        ],
        "total_tokens": 0,
        "iterations": 1,
        "final_answer": "",
        "status": "failed",
        "error_message": error,
        "response_time_ms": elapsed_ms,
        "runner": "http",
        "endpoint": endpoint,
        "protocol_version": PROTOCOL_VERSION,
    }


def parse_http_body(
    *,
    status_code: int,
    text: str,
    content_type: str,
    query: str = "",
    elapsed_ms: int = 0,
    endpoint: str = "",
) -> dict[str, Any]:
    """Parse raw HTTP status/body into a pipeline result dict."""
    if status_code >= 400:
        body_preview = (text or "")[:500]
        return failed_http_result(
            query=query,
            error=f"HTTP {status_code}: {body_preview}",
            elapsed_ms=elapsed_ms,
            endpoint=endpoint,
        )

    ct = (content_type or "").lower()
    data: Any
    if "application/json" in ct or (text or "").lstrip().startswith(("{", "[")):
        import json

        try:
            data = json.loads(text) if text else {}
        except ValueError:
            data = {"answer": text}
    else:
        data = {"answer": text or ""}

    return coerce_http_response(
        data, query=query, elapsed_ms=elapsed_ms, endpoint=endpoint
    )

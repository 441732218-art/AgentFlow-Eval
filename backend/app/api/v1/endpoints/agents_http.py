# (c) 2026 AgentFlow-Eval
"""HTTP Agent product APIs — contract docs + probe (Phase 1)."""

from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.core.agent_runner.protocol import (
    PROTOCOL_VERSION,
    build_http_request_payload,
    coerce_http_response,
    failed_http_result,
)
from app.core.agent_runner.ssrf import SsrfBlockedError, validate_http_agent_url
from app.core.rbac import Permission, require_permission

router = APIRouter()


class HttpAgentProbeRequest(BaseModel):
    """Probe an external HTTP agent endpoint."""

    endpoint_url: str = Field(..., min_length=1, description="Absolute http(s) URL")
    timeout_sec: float = Field(default=10.0, ge=1.0, le=120.0)
    headers: dict[str, str] = Field(default_factory=dict)
    method: str = Field(default="POST")
    query: str = Field(default="ping", description="Probe query string")
    context: dict[str, Any] = Field(default_factory=dict)
    verify_ssl: bool = True


class HttpAgentProbeResponse(BaseModel):
    """Probe result — always JSON (use ok/reachable for UX, not only HTTP status)."""

    ok: bool = False
    reachable: bool = False
    protocol_compatible: bool = False
    ssrf_blocked: bool = False
    latency_ms: int | None = None
    http_status: int | None = None
    endpoint: str = ""
    protocol_version: str = PROTOCOL_VERSION
    final_answer_preview: str = ""
    steps_count: int = 0
    normalized_status: str = ""
    error: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


@router.get("/contract")
@require_permission(Permission.TASK_READ)
async def http_agent_contract(request: Request) -> dict[str, Any]:
    """Return agentflow.http.v1 contract summary for UI / integrators."""
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request": {
            "method": "POST",
            "content_type": "application/json",
            "body": {
                "protocol_version": PROTOCOL_VERSION,
                "query": "string",
                "tools": ["string"],
                "context": {},
                "meta": {},
            },
        },
        "response_accepted": [
            {
                "name": "full",
                "example": {
                    "status": "success",
                    "final_answer": "...",
                    "steps": [],
                    "total_tokens": 0,
                    "response_time_ms": 0,
                },
            },
            {"name": "short", "example": {"answer": "..."}},
            {"name": "plain_text", "example": "raw answer body"},
        ],
        "agent_config_fields": {
            "runner": "http | http_agent | remote | webhook",
            "endpoint_url": "https://agent.example.com/v1/invoke",
            "timeout_sec": 60,
            "headers": {"Authorization": "Bearer ..."},
            "method": "POST",
            "context": {},
            "verify_ssl": True,
        },
        "docs": "docs/http-agent-protocol.md",
    }


@router.post("/probe", response_model=HttpAgentProbeResponse)
@require_permission(Permission.TASK_CREATE, Permission.TASK_EXECUTE)
async def probe_http_agent(
    body: HttpAgentProbeRequest,
    request: Request,
) -> HttpAgentProbeResponse:
    """Probe an external HTTP agent: SSRF check, reachability, protocol normalize."""
    allow_private = bool(getattr(settings, "HTTP_AGENT_ALLOW_PRIVATE_IP", False))
    endpoint = (body.endpoint_url or "").strip()

    try:
        endpoint = validate_http_agent_url(endpoint, allow_private=allow_private)
    except SsrfBlockedError as exc:
        return HttpAgentProbeResponse(
            ok=False,
            reachable=False,
            protocol_compatible=False,
            ssrf_blocked=True,
            endpoint=endpoint or body.endpoint_url,
            error=str(exc),
            detail={"code": "ssrf_blocked"},
        )

    method = (body.method or "POST").upper()
    payload = build_http_request_payload(
        body.query or "ping",
        tools=[],
        context=body.context or {},
        meta={"probe": True},
    )
    headers = {"Content-Type": "application/json", **(body.headers or {})}

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=float(body.timeout_sec),
            verify=bool(body.verify_ssl),
        ) as client:
            resp = await client.request(
                method,
                endpoint,
                json=payload if method in {"POST", "PUT", "PATCH"} else None,
                params=payload if method == "GET" else None,
                headers=headers,
            )
        latency = int((time.monotonic() - t0) * 1000)
    except httpx.TimeoutException as exc:
        return HttpAgentProbeResponse(
            ok=False,
            reachable=False,
            protocol_compatible=False,
            latency_ms=int((time.monotonic() - t0) * 1000),
            endpoint=endpoint,
            error=f"Timeout after {body.timeout_sec}s: {exc}",
            detail={"code": "timeout"},
        )
    except httpx.HTTPError as exc:
        return HttpAgentProbeResponse(
            ok=False,
            reachable=False,
            protocol_compatible=False,
            latency_ms=int((time.monotonic() - t0) * 1000),
            endpoint=endpoint,
            error=f"HTTP request failed: {exc}",
            detail={"code": "http_error"},
        )

    # Normalize via Phase-0 protocol
    if resp.status_code >= 400:
        normalized = failed_http_result(
            query=body.query or "ping",
            error=f"HTTP {resp.status_code}: {(resp.text or '')[:300]}",
            elapsed_ms=latency,
            endpoint=endpoint,
        )
        return HttpAgentProbeResponse(
            ok=False,
            reachable=True,
            protocol_compatible=False,
            latency_ms=latency,
            http_status=resp.status_code,
            endpoint=endpoint,
            error=normalized.get("error_message") or f"HTTP {resp.status_code}",
            normalized_status="failed",
            detail={"code": "http_status", "body_preview": (resp.text or "")[:200]},
        )

    ct = (resp.headers.get("content-type") or "").lower()
    data: Any
    if "application/json" in ct or (resp.text or "").lstrip().startswith(("{", "[")):
        try:
            data = resp.json()
        except ValueError:
            data = {"answer": resp.text}
    else:
        data = {"answer": resp.text or ""}

    normalized = coerce_http_response(
        data, query=body.query or "ping", elapsed_ms=latency, endpoint=endpoint
    )
    status = str(normalized.get("status") or "")
    final = str(normalized.get("final_answer") or "")
    steps = normalized.get("steps") or []
    # Compatible if we got success (or max_iter) with any answer/steps structure
    compatible = status in {"success", "max_iterations_reached"} and (
        bool(final) or bool(steps)
    )
    # Also accept failed with structured body as "reachable + protocol parseable"
    parseable = bool(normalized.get("runner") == "http")

    return HttpAgentProbeResponse(
        ok=compatible,
        reachable=True,
        protocol_compatible=compatible or parseable,
        latency_ms=latency,
        http_status=resp.status_code,
        endpoint=endpoint,
        final_answer_preview=final[:200],
        steps_count=len(steps) if isinstance(steps, list) else 0,
        normalized_status=status,
        error=None if compatible else (normalized.get("error_message") or "No usable answer"),
        detail={
            "code": "ok" if compatible else "protocol_partial",
            "total_tokens": normalized.get("total_tokens"),
        },
    )

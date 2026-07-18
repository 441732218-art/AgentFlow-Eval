# (c) 2026 AgentFlow-Eval
"""HTTP Agent Runner — call a user-hosted Agent HTTP service.

Contract (request POST JSON)::

    {
      "query": "<user query>",
      "tools": ["web_search", ...],   # optional
      "context": { ... }              # optional passthrough from agent_config
    }

Accepted response shapes (any one)::

    1. Full:  { "steps": [...], "final_answer": "...", "status": "success",
                "total_tokens": 0, "response_time_ms": 0, "error_message": "" }
    2. Short: { "answer": "..." } or { "output": "..." } or { "final_answer": "..." }
    3. Plain text body (Content-Type: text/plain)

Status mapping: success | failed | max_iterations_reached (default success if answer present).
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.agent_runner.base import BaseAgentRunner

logger = logging.getLogger(__name__)


class HttpAgentRunner(BaseAgentRunner):
    """Invoke an external Agent over HTTP and normalize the response.

    Designed for enterprise users who already operate their own agent service
    and want AgentFlow-Eval only for suite execution, tracing, and judging.
    """

    def __init__(
        self,
        endpoint_url: str,
        *,
        timeout_sec: float = 60.0,
        headers: dict[str, str] | None = None,
        method: str = "POST",
        context: dict[str, Any] | None = None,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize the HTTP runner.

        Args:
            endpoint_url: Full URL of the agent endpoint.
            timeout_sec: Request timeout in seconds.
            headers: Extra HTTP headers (e.g. Authorization).
            method: HTTP method (POST recommended).
            context: Extra JSON fields merged into the request body.
            verify_ssl: Whether to verify TLS certificates.
        """
        if not endpoint_url or not str(endpoint_url).strip():
            raise ValueError("endpoint_url is required for HttpAgentRunner")
        self.endpoint_url = str(endpoint_url).strip()
        self.timeout_sec = float(timeout_sec)
        self.headers = dict(headers or {})
        self.method = (method or "POST").upper()
        self.context = dict(context or {})
        self.verify_ssl = verify_ssl

    async def run(
        self,
        query: str,
        tools: list[dict[str, Any]] | list[str] | None = None,
    ) -> dict[str, Any]:
        """Call the remote agent and return a pipeline-compatible result dict.

        Args:
            query: User query string.
            tools: Optional tool definitions (OpenAI-style dicts) or name list.

        Returns:
            Dict with steps, final_answer, status, total_tokens, response_time_ms, etc.
        """
        start = time.monotonic()
        tool_names = self._extract_tool_names(tools)
        payload: dict[str, Any] = {
            "query": query,
            "tools": tool_names,
        }
        if self.context:
            payload["context"] = self.context

        headers = {"Content-Type": "application/json", **self.headers}

        try:
            from app.core.observability.aols import LogEvent, emit_agent, new_execution_id

            _exec_id = new_execution_id()
            emit_agent(
                LogEvent.AGENT_STARTED,
                execution_id=_exec_id,
                agent_id="http_runner",
                agent_version="1.0",
            )
        except Exception:
            _exec_id = None

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_sec,
                verify=self.verify_ssl,
            ) as client:
                response = await client.request(
                    self.method,
                    self.endpoint_url,
                    json=payload if self.method in {"POST", "PUT", "PATCH"} else None,
                    params=payload if self.method == "GET" else None,
                    headers=headers,
                )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            try:
                from app.core.observability.aols import LogEvent, emit_agent

                emit_agent(
                    LogEvent.AGENT_COMPLETED,
                    execution_id=_exec_id,
                    agent_id="http_runner",
                    duration_ms=elapsed_ms,
                    status="success",
                    http_status=response.status_code,
                )
            except Exception:
                pass
            return self._normalize_response(response, query=query, elapsed_ms=elapsed_ms)
        except httpx.TimeoutException as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning("HttpAgentRunner timeout: %s", exc)
            try:
                from app.core.observability.aols import LogEvent, emit_agent

                emit_agent(
                    LogEvent.AGENT_FAILED,
                    execution_id=_exec_id,
                    agent_id="http_runner",
                    duration_ms=elapsed_ms,
                    status="timeout",
                    error_message=str(exc),
                )
            except Exception:
                pass
            return self._failed_result(
                query=query,
                error=f"HTTP agent timeout after {self.timeout_sec}s: {exc}",
                elapsed_ms=elapsed_ms,
            )
        except httpx.HTTPError as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning("HttpAgentRunner HTTP error: %s", exc)
            try:
                from app.core.observability.aols import LogEvent, emit_agent

                emit_agent(
                    LogEvent.AGENT_FAILED,
                    execution_id=_exec_id,
                    agent_id="http_runner",
                    duration_ms=elapsed_ms,
                    status="http_error",
                    error_message=str(exc),
                )
            except Exception:
                pass
            return self._failed_result(
                query=query,
                error=f"HTTP agent request failed: {exc}",
                elapsed_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.exception("HttpAgentRunner unexpected error: %s", exc)
            try:
                from app.core.observability.aols import LogEvent, emit_agent

                emit_agent(
                    LogEvent.AGENT_FAILED,
                    execution_id=_exec_id,
                    agent_id="http_runner",
                    duration_ms=elapsed_ms,
                    status="failed",
                    error_message=str(exc),
                )
            except Exception:
                pass
            return self._failed_result(
                query=query,
                error=str(exc),
                elapsed_ms=elapsed_ms,
            )

    # BaseAgentRunner abstract signature uses different param names; keep both.
    async def run_with_config(  # pragma: no cover - alias for base ABC
        self,
        user_query: str,
        agent_config: dict[str, Any],
    ) -> Any:
        return await self.run(user_query, tools=agent_config.get("tools"))

    @staticmethod
    def _extract_tool_names(
        tools: list[dict[str, Any]] | list[str] | None,
    ) -> list[str]:
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

    def _normalize_response(
        self,
        response: httpx.Response,
        *,
        query: str,
        elapsed_ms: int,
    ) -> dict[str, Any]:
        if response.status_code >= 400:
            body_preview = (response.text or "")[:500]
            return self._failed_result(
                query=query,
                error=f"HTTP {response.status_code}: {body_preview}",
                elapsed_ms=elapsed_ms,
            )

        content_type = (response.headers.get("content-type") or "").lower()
        data: Any
        if "application/json" in content_type or (response.text or "").lstrip().startswith(("{", "[")):
            try:
                data = response.json()
            except ValueError:
                data = {"answer": response.text}
        else:
            data = {"answer": response.text or ""}

        if isinstance(data, str):
            data = {"answer": data}
        if not isinstance(data, dict):
            return self._failed_result(
                query=query,
                error=f"Unexpected response type: {type(data).__name__}",
                elapsed_ms=elapsed_ms,
            )

        final_answer = (
            data.get("final_answer")
            or data.get("answer")
            or data.get("output")
            or data.get("result")
            or ""
        )
        steps = data.get("steps")
        if not isinstance(steps, list) or not steps:
            steps = [
                {
                    "iteration": 0,
                    "thought": "HTTP agent response",
                    "action": "final_answer",
                    "action_input": str(final_answer),
                    "observation": "",
                    "tokens": int(data.get("total_tokens") or 0),
                }
            ]

        status = str(data.get("status") or ("success" if final_answer else "failed"))
        if status not in {"success", "failed", "max_iterations_reached"}:
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
            "endpoint": self.endpoint_url,
        }

    @staticmethod
    def _failed_result(
        *,
        query: str,
        error: str,
        elapsed_ms: int,
    ) -> dict[str, Any]:
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
        }

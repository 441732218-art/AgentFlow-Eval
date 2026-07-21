# (c) 2026 AgentFlow-Eval
"""HTTP Agent Runner — call a user-hosted Agent HTTP service.

Protocol: ``agentflow.http.v1`` — see ``protocol.py`` and
``docs/http-agent-protocol.md``.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.agent_runner.base import BaseAgentRunner
from app.core.agent_runner.protocol import (
    PROTOCOL_VERSION,
    build_http_request_payload,
    coerce_http_response,
    extract_tool_names,
    failed_http_result,
)

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
        *,
        agent_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call the remote agent and return a pipeline-compatible result dict.

        Args:
            query: User query string.
            tools: Optional tool definitions (OpenAI-style dicts) or name list.
            agent_config: Optional full config; ``context`` / ``meta`` may merge.

        Returns:
            Dict with steps, final_answer, status, total_tokens, response_time_ms.
        """
        start = time.monotonic()
        cfg = dict(agent_config or {})
        context = dict(self.context)
        extra_ctx = cfg.get("context")
        if isinstance(extra_ctx, dict):
            context.update(extra_ctx)
        meta: dict[str, Any] = {"protocol_version": PROTOCOL_VERSION}
        extra_meta = cfg.get("meta")
        if isinstance(extra_meta, dict):
            meta.update(extra_meta)

        payload = build_http_request_payload(
            query,
            tools=tools,
            context=context,
            meta=meta,
        )
        headers = {"Content-Type": "application/json", **self.headers}

        try:
            from app.core.observability.aols import (
                LogEvent,
                emit_agent,
                new_execution_id,
            )

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
            return self._normalize_response(
                response, query=query, elapsed_ms=elapsed_ms
            )
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
            return failed_http_result(
                query=query,
                error=f"HTTP agent timeout after {self.timeout_sec}s: {exc}",
                elapsed_ms=elapsed_ms,
                endpoint=self.endpoint_url,
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
            return failed_http_result(
                query=query,
                error=f"HTTP agent request failed: {exc}",
                elapsed_ms=elapsed_ms,
                endpoint=self.endpoint_url,
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
            return failed_http_result(
                query=query,
                error=str(exc),
                elapsed_ms=elapsed_ms,
                endpoint=self.endpoint_url,
            )

    def _normalize_response(
        self,
        response: httpx.Response,
        *,
        query: str,
        elapsed_ms: int,
    ) -> dict[str, Any]:
        if response.status_code >= 400:
            body_preview = (response.text or "")[:500]
            return failed_http_result(
                query=query,
                error=f"HTTP {response.status_code}: {body_preview}",
                elapsed_ms=elapsed_ms,
                endpoint=self.endpoint_url,
            )

        content_type = (response.headers.get("content-type") or "").lower()
        data: Any
        # Prefer .json() when available (real httpx + unit mocks expose it)
        if "application/json" in content_type or (response.text or "").lstrip().startswith(
            ("{", "[")
        ):
            try:
                data = response.json()
            except ValueError:
                data = {"answer": response.text}
        else:
            data = {"answer": response.text or ""}

        return coerce_http_response(
            data,
            query=query,
            elapsed_ms=elapsed_ms,
            endpoint=self.endpoint_url,
        )

    # Back-compat aliases used by older unit tests
    _extract_tool_names = staticmethod(extract_tool_names)
    _failed_result = staticmethod(
        lambda **kwargs: failed_http_result(
            query=kwargs.get("query", ""),
            error=kwargs.get("error", ""),
            elapsed_ms=int(kwargs.get("elapsed_ms") or 0),
            endpoint=str(kwargs.get("endpoint") or ""),
        )
    )

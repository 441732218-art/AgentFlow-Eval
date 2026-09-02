# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""HTTP transport implementation for ``RemoteToolClient``."""

from __future__ import annotations

from typing import Any

import httpx

from app.runtime.tools.credential_resolver import CredentialResolver
from app.runtime.tools.errors import (
    RemoteAuthError,
    RemoteProviderError,
    RemoteResponseValidationError,
    RemoteTimeoutError,
    ToolExecutionError,
)
from app.runtime.tools.policy import RemoteExecutionPolicy
from app.runtime.tools.provider import ToolProviderRequest, ToolProviderResponse
from app.runtime.tools.remote_client import RemoteToolClient

_FORBIDDEN_METADATA_KEYS = frozenset(
    {"api_key", "secret", "token", "password", "authorization"}
)


class HttpRemoteToolClient(RemoteToolClient):
    """Production HTTP transport for remote tool provider requests.

    Performs a single HTTP round-trip per ``send`` call. Retry and overall
    timeout policy are enforced by ``RemoteToolExecutorAdapter`` via
    ``RemoteExecutionPolicy``.
    """

    def __init__(
        self,
        *,
        credential_resolver: CredentialResolver | None = None,
        remote_policy: RemoteExecutionPolicy | None = None,
        timeout_seconds: float | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        policy = remote_policy or RemoteExecutionPolicy()
        resolved_timeout = (
            timeout_seconds if timeout_seconds is not None else policy.timeout_seconds
        )
        if resolved_timeout <= 0:
            raise ValueError("timeout_seconds must be > 0")
        self._credential_resolver = credential_resolver
        self._timeout_seconds = resolved_timeout
        self._http_client = http_client

    def send(self, request: ToolProviderRequest) -> ToolProviderResponse:
        endpoint = self._resolve_endpoint(request)
        headers = self._build_headers(request)
        payload = {
            "name": request.tool_name,
            "arguments": dict(request.arguments),
            "metadata": dict(request.metadata),
        }

        try:
            response = self._post(endpoint, payload, headers)
        except httpx.TimeoutException as exc:
            raise RemoteTimeoutError(
                f"HTTP request timed out ({self._timeout_seconds}s)",
                tool_name=request.tool_name,
                cause=exc,
            ) from exc
        except ToolExecutionError:
            raise
        except httpx.HTTPError as exc:
            raise RemoteProviderError(
                f"HTTP transport failed for {request.tool_name}",
                tool_name=request.tool_name,
                cause=exc,
            ) from exc

        return self._map_http_response(response, request.tool_name)

    def _post(
        self,
        endpoint: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self._timeout_seconds,
            )
        with httpx.Client(timeout=self._timeout_seconds) as client:
            return client.post(endpoint, json=payload, headers=headers)

    @staticmethod
    def _resolve_endpoint(request: ToolProviderRequest) -> str:
        endpoint = (request.metadata.get("endpoint") or "").strip()
        if not endpoint:
            raise RemoteProviderError(
                "Remote tool request metadata must include endpoint",
                tool_name=request.tool_name,
            )
        return endpoint

    def _build_headers(self, request: ToolProviderRequest) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        auth_block = request.metadata.get("auth")
        if not isinstance(auth_block, dict):
            return headers

        auth_type = str(auth_block.get("auth_type", "none")).strip()
        if auth_type == "none":
            return headers

        credential_ref = auth_block.get("credential_ref")
        if not credential_ref or not str(credential_ref).strip():
            raise RemoteAuthError(
                f"HTTP {401}: missing credential_ref for auth_type={auth_type}",
                tool_name=request.tool_name,
            )
        if self._credential_resolver is None:
            raise RemoteAuthError(
                f"HTTP {401}: credential resolver not configured",
                tool_name=request.tool_name,
            )

        try:
            secret = self._credential_resolver.resolve(str(credential_ref))
        except KeyError as exc:
            raise RemoteAuthError(
                f"HTTP {401}: unknown credential_ref",
                tool_name=request.tool_name,
                cause=exc,
            ) from exc

        if auth_type in {"bearer_ref", "oauth_ref"}:
            headers["Authorization"] = f"Bearer {secret}"
        elif auth_type == "api_key_ref":
            headers["X-API-Key"] = secret
        else:
            raise RemoteAuthError(
                f"HTTP {401}: unsupported auth_type={auth_type}",
                tool_name=request.tool_name,
            )
        return headers

    @staticmethod
    def _map_http_response(response: httpx.Response, tool_name: str) -> ToolProviderResponse:
        status = response.status_code
        if status in (401, 403):
            raise RemoteAuthError(
                f"HTTP {status}: remote provider rejected authentication",
                tool_name=tool_name,
            )
        if status == 408:
            raise RemoteTimeoutError(
                f"HTTP {status}: remote provider request timeout",
                tool_name=tool_name,
            )
        if status >= 400:
            raise RemoteProviderError(
                f"HTTP {status}: remote provider error",
                tool_name=tool_name,
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise RemoteResponseValidationError(
                f"HTTP {status}: invalid JSON response",
                tool_name=tool_name,
                cause=exc,
            ) from exc

        if not isinstance(body, dict):
            raise RemoteResponseValidationError(
                f"HTTP {status}: response body must be a JSON object",
                tool_name=tool_name,
            )

        if "success" not in body:
            raise RemoteResponseValidationError(
                f"HTTP {status}: response must include success field",
                tool_name=tool_name,
            )

        success = body.get("success")
        if not isinstance(success, bool):
            raise RemoteResponseValidationError(
                f"HTTP {status}: response.success must be a bool",
                tool_name=tool_name,
            )

        if success is False:
            error_message = (body.get("error") or "").strip()
            raise RemoteProviderError(
                error_message or f"Remote provider failed for {tool_name}",
                tool_name=tool_name,
            )

        metadata = body.get("metadata", {})
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise RemoteResponseValidationError(
                f"HTTP {status}: response.metadata must be a dict",
                tool_name=tool_name,
            )

        HttpRemoteToolClient._assert_safe_metadata(metadata)

        return ToolProviderResponse(
            success=True,
            output=body.get("output"),
            error=None,
            metadata=dict(metadata),
        )

    @staticmethod
    def _assert_safe_metadata(payload: dict[str, Any]) -> None:
        for key in payload:
            if key.lower() in _FORBIDDEN_METADATA_KEYS:
                raise RemoteResponseValidationError(
                    "HTTP response metadata must not contain secret field names",
                )

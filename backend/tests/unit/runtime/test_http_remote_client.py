# AgentFlow Intelligence v2.0 — HttpRemoteToolClient unit tests (Phase 8.6)

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.runtime.tools.auth import ToolProviderAuth
from app.runtime.tools.credential_resolver import InMemoryCredentialResolver
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.errors import (
    RemoteAuthError,
    RemoteProviderError,
    RemoteTimeoutError,
)
from app.runtime.tools.factory import create_tool_execution_engine
from app.runtime.tools.http_client import HttpRemoteToolClient
from app.runtime.tools.policy import RemoteExecutionPolicy
from app.runtime.tools.provider import ToolProviderRequest, ToolProviderResponse
from app.runtime.tools.registry import create_tool_registry, reset_tool_registry
from app.runtime.tools.remote_adapter import RemoteToolExecutorAdapter


_MOCK_ENDPOINT = "http://mock.test/tools/invoke"


def _request(
    *,
    tool_name: str = "example.remote",
    arguments: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ToolProviderRequest:
    return ToolProviderRequest(
        tool_name=tool_name,
        arguments=arguments or {"query": "test"},
        metadata=metadata
        or {
            "endpoint": _MOCK_ENDPOINT,
            "provider_id": "mock-provider",
        },
    )


def _http_client(handler) -> HttpRemoteToolClient:
    transport = httpx.MockTransport(handler)
    return HttpRemoteToolClient(
        http_client=httpx.Client(transport=transport),
        timeout_seconds=5.0,
    )


def test_successful_request_returns_tool_provider_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        import json

        assert str(request.url) == _MOCK_ENDPOINT
        payload = json.loads(request.content.decode())
        assert payload["tool_name"] == "example.remote"
        return httpx.Response(
            200,
            json={"success": True, "output": {"received": payload["arguments"]}},
        )

    client = _http_client(handler)
    response = client.send(_request())

    assert isinstance(response, ToolProviderResponse)
    assert response.success is True
    assert response.output == {"received": {"query": "test"}}


@pytest.mark.parametrize("status_code", [401, 403])
def test_auth_status_raises_remote_auth_error(status_code: int) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    client = _http_client(handler)

    with pytest.raises(RemoteAuthError, match=f"HTTP {status_code}"):
        client.send(_request())


def test_timeout_raises_remote_timeout_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = _http_client(handler)

    with pytest.raises(RemoteTimeoutError, match="timed out"):
        client.send(_request())


def test_http_500_raises_remote_provider_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = _http_client(handler)

    with pytest.raises(RemoteProviderError, match="HTTP 500"):
        client.send(_request())


def test_invalid_json_raises_remote_provider_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    client = _http_client(handler)

    with pytest.raises(RemoteProviderError, match="invalid JSON"):
        client.send(_request())


def test_adapter_retries_timeout_then_succeeds() -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(
            200,
            json={"success": True, "output": {"attempt": attempts["count"]}},
        )

    http_client = _http_client(handler)
    policy = RemoteExecutionPolicy(max_retries=2, timeout_seconds=5.0)
    adapter = RemoteToolExecutorAdapter(http_client, policy=policy)
    definition = ToolDefinition(
        name="example.remote",
        description="remote example",
        executor_type="remote",
        input_schema={"type": "object"},
        metadata={"endpoint": _MOCK_ENDPOINT},
    )

    output = adapter.execute(definition, {"query": "retry"})

    assert output == {"attempt": 3}
    assert attempts["count"] == 3


def test_auth_resolves_credential_ref_into_header_not_trace() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("Authorization", "")
        return httpx.Response(200, json={"success": True, "output": {"ok": True}})

    resolver = InMemoryCredentialResolver(
        {"vault://example/token": "resolved-secret-token"}
    )
    transport = httpx.MockTransport(handler)
    client = HttpRemoteToolClient(
        credential_resolver=resolver,
        http_client=httpx.Client(transport=transport),
    )
    auth = ToolProviderAuth(
        auth_type="bearer_ref",
        credential_ref="vault://example/token",
    )
    request = ToolProviderRequest(
        tool_name="example.remote",
        arguments={"query": "auth"},
        metadata={
            "endpoint": _MOCK_ENDPOINT,
            "auth": auth.to_metadata(),
        },
    )

    client.send(request)

    assert captured["authorization"] == "Bearer resolved-secret-token"

    observation = RemoteToolExecutorAdapter.build_observation(
        tool_name="example.remote",
        executor_type="remote",
        duration_seconds=0.1,
        status="success",
    )
    safe_metadata = auth.to_metadata()
    forbidden_values = ("resolved-secret-token", "Bearer resolved-secret-token")

    for value in forbidden_values:
        assert value not in observation.values()
        assert value not in safe_metadata.values()
    assert safe_metadata["credential_ref"] == "vault://example/token"


def test_end_to_end_via_registry_and_engine() -> None:
    reset_tool_registry()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"success": True, "output": {"via": "http"}},
        )

    registry = create_tool_registry(bootstrap=True)
    http_client = _http_client(handler)
    engine = create_tool_execution_engine(remote_client=http_client)

    definition = registry.get("example.remote_search")
    result = engine.execute(definition, {"query": "e2e"})

    assert result.tool_name == "example.remote_search"
    assert result.executor_type == "remote"
    assert result.output == {"via": "http"}

    reset_tool_registry()

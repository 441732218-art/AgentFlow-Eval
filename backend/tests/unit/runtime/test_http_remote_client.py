# AgentFlow Intelligence v2.0 — HttpRemoteToolClient unit tests (Phase 9.2)

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from app.runtime.tools.auth import ToolProviderAuth
from app.runtime.tools.credential_resolver import InMemoryCredentialResolver
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.errors import (
    RemoteAuthError,
    RemoteProviderError,
    RemoteResponseValidationError,
    RemoteTimeoutError,
)
from app.runtime.tools.factory import (
    create_http_remote_tool_client,
    create_tool_execution_engine,
)
from app.runtime.tools.http_client import HttpRemoteToolClient
from app.runtime.tools.policy import RemoteExecutionPolicy
from app.runtime.tools.provider import ToolProviderRequest, ToolProviderResponse
from app.runtime.tools.registry import create_tool_registry, reset_tool_registry
from app.runtime.tools.remote_adapter import RemoteToolExecutorAdapter

_MOCK_ENDPOINT = "http://mock.test/tools/invoke"
_RUNTIME_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime"
_FORBIDDEN_RUNTIME_STRINGS = (
    "trade.search_customer",
    "trade.generate_email",
    "trade_provider",
    "CRM",
    "Email",
)


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
        remote_policy=RemoteExecutionPolicy(timeout_seconds=5.0),
    )


def test_http_success_returns_tool_provider_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        import json

        payload = json.loads(request.content.decode())
        assert payload["name"] == "example.remote"
        return httpx.Response(
            200,
            json={"success": True, "output": {"result": "ok"}, "metadata": {}},
        )

    client = _http_client(handler)
    response = client.send(_request())

    assert isinstance(response, ToolProviderResponse)
    assert response.success is True
    assert response.output == {"result": "ok"}


def test_provider_failure_raises_remote_provider_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"success": False, "error": "provider failed"},
        )

    client = _http_client(handler)

    with pytest.raises(RemoteProviderError, match="provider failed"):
        client.send(_request())


def test_timeout_raises_remote_timeout_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = _http_client(handler)

    with pytest.raises(RemoteTimeoutError, match="timed out"):
        client.send(_request())


def test_missing_success_raises_remote_response_validation_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output": {"result": "ok"}})

    client = _http_client(handler)

    with pytest.raises(RemoteResponseValidationError, match="success"):
        client.send(_request())


def test_invalid_json_raises_remote_response_validation_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    client = _http_client(handler)

    with pytest.raises(RemoteResponseValidationError, match="invalid JSON"):
        client.send(_request())


def test_credential_boundary_allows_ref_not_secrets_in_metadata() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("Authorization", "")
        return httpx.Response(
            200,
            json={"success": True, "output": {"ok": True}, "metadata": {}},
        )

    resolver = InMemoryCredentialResolver(
        {"vault://trade/provider": "resolved-secret-token"}
    )
    transport = httpx.MockTransport(handler)
    client = HttpRemoteToolClient(
        credential_resolver=resolver,
        http_client=httpx.Client(transport=transport),
    )
    auth = ToolProviderAuth(
        auth_type="bearer_ref",
        credential_ref="vault://trade/provider",
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
    safe_metadata = auth.to_metadata()
    assert safe_metadata["credential_ref"] == "vault://trade/provider"
    for forbidden in ("secret", "token", "api_key", "password"):
        assert forbidden not in safe_metadata


@pytest.mark.parametrize("status_code", [401, 403])
def test_auth_status_raises_remote_auth_error(status_code: int) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    client = _http_client(handler)

    with pytest.raises(RemoteAuthError, match=f"HTTP {status_code}"):
        client.send(_request())


def test_http_500_raises_remote_provider_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = _http_client(handler)

    with pytest.raises(RemoteProviderError, match="HTTP 500"):
        client.send(_request())


def test_adapter_retries_timeout_then_succeeds() -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(
            200,
            json={"success": True, "output": {"attempt": attempts["count"]}, "metadata": {}},
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


def test_factory_create_http_remote_tool_client_uses_policy_timeout() -> None:
    policy = RemoteExecutionPolicy(timeout_seconds=12.5)
    client = create_http_remote_tool_client(remote_policy=policy)
    assert client._timeout_seconds == 12.5


def test_factory_create_tool_execution_engine_accepts_http_client() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"success": True, "output": {"via": "factory"}, "metadata": {}},
        )

    http_client = _http_client(handler)
    engine = create_tool_execution_engine(remote_client=http_client)
    definition = ToolDefinition(
        name="factory.remote",
        description="factory remote",
        executor_type="remote",
        input_schema={"type": "object"},
        metadata={"endpoint": _MOCK_ENDPOINT},
    )

    result = engine.execute(definition, {"query": "x"})
    assert result.output == {"via": "factory"}


def test_end_to_end_via_registry_and_engine() -> None:
    reset_tool_registry()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"success": True, "output": {"via": "http"}, "metadata": {}},
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


def test_runtime_core_has_no_trade_or_business_leakage() -> None:
    for path in _RUNTIME_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_RUNTIME_STRINGS:
            assert forbidden not in source, f"{forbidden!r} found in {path}"

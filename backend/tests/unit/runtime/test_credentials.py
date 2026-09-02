# AgentFlow Intelligence v2.0 — Credential resolution tests (Phase 9.3)

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.runtime.tools.auth import ToolProviderAuth
from app.runtime.tools.credential_resolver import (
    CredentialNotFoundError,
    InMemoryCredentialResolver,
)
from app.runtime.tools.factory import create_env_credential_resolver
from app.runtime.tools.http_client import HttpRemoteToolClient
from app.runtime.tools.provider import ToolProviderRequest
from app.runtime.tools.remote_adapter import RemoteToolExecutorAdapter
from app.runtime.tools.resolvers.env_resolver import EnvCredentialResolver

_MOCK_ENDPOINT = "http://mock.test/tools/invoke"
_RUNTIME_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime"
_TEST_ROOT = Path(__file__).resolve().parents[3] / "tests" / "unit" / "runtime"
_SECRET_VALUE = "super-secret-api-key-value"


def test_env_credential_resolves_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRM_API_KEY", _SECRET_VALUE)
    resolver = EnvCredentialResolver()

    credentials = resolver.resolve("env://CRM_API_KEY")

    assert credentials == {"api_key": _SECRET_VALUE}


def test_missing_environment_variable_raises_credential_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CRM_API_KEY", raising=False)
    resolver = EnvCredentialResolver()

    with pytest.raises(CredentialNotFoundError, match="env://CRM_API_KEY"):
        resolver.resolve("env://CRM_API_KEY")


def test_http_client_uses_env_resolved_credential_in_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CRM_API_KEY", _SECRET_VALUE)
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["x_api_key"] = request.headers.get("X-API-Key", "")
        return httpx.Response(
            200,
            json={"success": True, "output": {"ok": True}, "metadata": {}},
        )

    transport = httpx.MockTransport(handler)
    client = HttpRemoteToolClient(
        credential_resolver=create_env_credential_resolver(),
        http_client=httpx.Client(transport=transport),
    )
    auth = ToolProviderAuth(
        auth_type="api_key_ref",
        credential_ref="env://CRM_API_KEY",
    )
    request = ToolProviderRequest(
        tool_name="remote.tool",
        arguments={"query": "x"},
        metadata={"endpoint": _MOCK_ENDPOINT, "auth": auth.to_metadata()},
    )

    client.send(request)

    assert captured["x_api_key"] == _SECRET_VALUE


def test_secret_never_appears_in_observation_or_error_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CRM_API_KEY", raising=False)
    client = HttpRemoteToolClient(credential_resolver=create_env_credential_resolver())
    auth = ToolProviderAuth(
        auth_type="api_key_ref",
        credential_ref="env://CRM_API_KEY",
    )
    request = ToolProviderRequest(
        tool_name="remote.tool",
        arguments={},
        metadata={"endpoint": _MOCK_ENDPOINT, "auth": auth.to_metadata()},
    )

    with pytest.raises(Exception) as exc_info:
        client.send(request)

    error_text = str(exc_info.value)
    assert _SECRET_VALUE not in error_text
    assert "super-secret" not in error_text

    observation = RemoteToolExecutorAdapter.build_observation(
        tool_name="remote.tool",
        executor_type="remote",
        duration_seconds=0.1,
        status="error",
        error_type=type(exc_info.value).__name__,
    )
    observation_text = str(observation)
    assert _SECRET_VALUE not in observation_text
    for forbidden in ("api_key=", "secret=", "token="):
        assert forbidden not in observation_text


def test_in_memory_resolver_returns_dict_for_http_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNUSED", "ignored")
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("Authorization", "")
        return httpx.Response(
            200,
            json={"success": True, "output": {"ok": True}, "metadata": {}},
        )

    resolver = InMemoryCredentialResolver(
        {"vault://example/token": {"token": "bearer-token-value"}}
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
        tool_name="remote.tool",
        arguments={},
        metadata={"endpoint": _MOCK_ENDPOINT, "auth": auth.to_metadata()},
    )

    client.send(request)

    assert captured["authorization"] == "Bearer bearer-token-value"


def test_runtime_source_has_no_hardcoded_secrets_outside_tests() -> None:
    forbidden_patterns = ('api_key="', "secret=", "token=")
    for path in _RUNTIME_ROOT.rglob("*.py"):
        if _TEST_ROOT in path.parents:
            continue
        source = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in source, f"{pattern!r} found in {path}"

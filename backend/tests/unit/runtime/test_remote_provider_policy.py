# AgentFlow Intelligence v2.0 — Remote Provider Policy unit tests (Phase 8.3)

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from app.runtime.tools.auth import FORBIDDEN_CREDENTIAL_FIELDS, ToolProviderAuth
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.errors import RemoteProviderError, RemoteTimeoutError, ToolInputValidationError
from app.runtime.tools.policy import RemoteExecutionPolicy
from app.runtime.tools.provider import ToolProviderRequest, ToolProviderResponse
from app.runtime.tools.remote_adapter import RemoteToolExecutorAdapter
from app.runtime.tools.remote_client import InMemoryRemoteClient
from app.runtime.tools.validation import validate_arguments


def _remote_definition(
    *,
    input_schema: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ToolDefinition:
    return ToolDefinition(
        name="external.capability",
        description="Remote capability stub",
        executor_type="remote",
        input_schema=input_schema or {"type": "object"},
        metadata=metadata or {"provider_id": "stub-provider"},
    )


def test_auth_contains_only_reference() -> None:
    auth = ToolProviderAuth(auth_type="api_key_ref", credential_ref="vault://provider/key")

    assert auth.auth_type == "api_key_ref"
    assert auth.credential_ref == "vault://provider/key"
    assert auth.to_metadata() == {
        "auth_type": "api_key_ref",
        "credential_ref": "vault://provider/key",
    }

    fields = {field.name for field in dataclasses.fields(ToolProviderAuth)}
    assert fields == {"auth_type", "credential_ref"}
    assert fields.isdisjoint(FORBIDDEN_CREDENTIAL_FIELDS)


def test_auth_rejects_secret_fields_in_metadata() -> None:
    with pytest.raises(ValueError, match="secret fields"):
        ToolProviderAuth.from_metadata(
            {"auth": {"auth_type": "api_key_ref", "api_key": "sk-live-secret"}}
        )


def test_invalid_arguments_rejected() -> None:
    schema = {
        "type": "object",
        "required": ["query"],
        "properties": {"query": {"type": "string"}},
    }

    with pytest.raises(ToolInputValidationError, match="Missing required argument"):
        validate_arguments(schema, {})

    with pytest.raises(ToolInputValidationError, match="must be of type string"):
        validate_arguments(schema, {"query": 123})

    adapter = RemoteToolExecutorAdapter(InMemoryRemoteClient())
    with pytest.raises(ToolInputValidationError):
        adapter.execute(_remote_definition(input_schema=schema), {})


def test_timeout_retry_policy() -> None:
    attempts = {"count": 0}

    def handler(_request: ToolProviderRequest) -> ToolProviderResponse:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RemoteTimeoutError("deadline exceeded")
        return ToolProviderResponse(success=True, output={"attempt": attempts["count"]})

    policy = RemoteExecutionPolicy(max_retries=1, timeout_seconds=30.0)
    adapter = RemoteToolExecutorAdapter(InMemoryRemoteClient(handler=handler), policy=policy)

    output = adapter.execute(_remote_definition(), {"query": "x"})

    assert output == {"attempt": 2}
    assert attempts["count"] == 2


def test_non_retryable_error_not_retried() -> None:
    attempts = {"count": 0}

    def handler(_request: ToolProviderRequest) -> ToolProviderResponse:
        attempts["count"] += 1
        raise ValueError("permanent transport failure")

    policy = RemoteExecutionPolicy(max_retries=3)
    adapter = RemoteToolExecutorAdapter(
        InMemoryRemoteClient(handler=handler),
        policy=policy,
    )

    with pytest.raises(RemoteProviderError):
        adapter.execute(_remote_definition(), {"query": "x"})

    assert attempts["count"] == 1


def test_secret_not_stored() -> None:
    auth = ToolProviderAuth(auth_type="bearer_ref", credential_ref="secret-store://token/main")
    payload = auth.to_metadata()

    for forbidden in ("api_key", "secret", "token", "password", "authorization"):
        assert forbidden not in payload
        assert forbidden not in dataclasses.asdict(auth)


def test_no_business_provider_dependency() -> None:
    source_path = RemoteToolExecutorAdapter.execute.__code__.co_filename
    with open(source_path, encoding="utf-8") as handle:
        source = handle.read().lower()
    for forbidden in ("crm", "email", "search", "requests.", "httpx"):
        assert forbidden not in source


def test_observation_contract_excludes_secrets() -> None:
    observation = RemoteToolExecutorAdapter.build_observation(
        tool_name="external.capability",
        executor_type="remote",
        duration_seconds=0.42,
        status="error",
        error_type="RemoteTimeoutError",
    )

    allowed = {"tool_name", "executor_type", "duration_seconds", "status", "error_type"}
    assert set(observation.keys()).issubset(allowed)
    for forbidden in ("token", "secret", "authorization", "password", "payload"):
        assert forbidden not in observation

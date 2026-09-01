# AgentFlow Intelligence v2.0 — Remote Tool Adapter unit tests (Phase 8.2.3)

from __future__ import annotations

from typing import Any

import pytest

from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.engine import ToolExecutionResult
from app.runtime.tools.errors import (
    RemoteProviderError,
    RemoteResponseValidationError,
    RemoteTimeoutError,
)
from app.runtime.tools.executor_registry import ToolExecutorRegistry
from app.runtime.tools.factory import create_tool_execution_engine
from app.runtime.tools.provider import (
    ToolProviderProtocol,
    ToolProviderRequest,
    ToolProviderResponse,
)
from app.runtime.tools.remote_adapter import RemoteToolExecutorAdapter
from app.runtime.tools.remote_client import InMemoryRemoteClient, RemoteToolClient


class StubRemoteProvider(ToolProviderProtocol):
    """In-process provider for contract tests (no business logic)."""

    def __init__(self) -> None:
        self.requests: list[ToolProviderRequest] = []

    def invoke(self, request: ToolProviderRequest) -> ToolProviderResponse:
        self.requests.append(request)
        return ToolProviderResponse(
            success=True,
            output={"received": request.arguments, "tool": request.tool_name},
            metadata={"provider": "stub"},
        )


def _remote_definition(name: str = "external.capability") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Remote capability stub",
        executor_type="remote",
        input_schema={"type": "object"},
        metadata={"provider_id": "stub-provider", "version": "1"},
    )


def test_remote_adapter_registered() -> None:
    registry = ToolExecutorRegistry()
    client = InMemoryRemoteClient()
    adapter = RemoteToolExecutorAdapter(client)

    registry.register(adapter)

    assert registry.get("remote") is adapter
    assert adapter.executor_type == "remote"


def test_remote_tool_definition_executes() -> None:
    provider = StubRemoteProvider()
    client = InMemoryRemoteClient(provider=provider)
    engine = create_tool_execution_engine(remote_client=client)
    definition = _remote_definition()

    result = engine.execute(definition, {"query": "value"})

    assert isinstance(result, ToolExecutionResult)
    assert result.tool_name == "external.capability"
    assert result.executor_type == "remote"
    assert result.output == {
        "received": {"query": "value"},
        "tool": "external.capability",
    }


def test_remote_client_called_with_contract() -> None:
    provider = StubRemoteProvider()
    client = InMemoryRemoteClient(provider=provider)
    adapter = RemoteToolExecutorAdapter(client)
    definition = _remote_definition(name="contract.check")

    adapter.execute(definition, {"key": "data"})

    assert len(client.calls) == 1
    request = client.calls[0]
    assert request.tool_name == "contract.check"
    assert request.arguments == {"key": "data"}
    assert request.metadata == {
        "provider_id": "stub-provider",
        "version": "1",
        "auth": {"auth_type": "none"},
    }
    assert len(provider.requests) == 1
    assert provider.requests[0] == request


def test_remote_error_mapping() -> None:
    client = InMemoryRemoteClient(
        handler=InMemoryRemoteClient.raising_provider(ValueError("transport broke"))
    )
    adapter = RemoteToolExecutorAdapter(client)

    with pytest.raises(RemoteProviderError) as exc:
        adapter.execute(_remote_definition(), {"x": 1})

    assert exc.value.tool_name == "external.capability"
    assert exc.value.cause is not None
    assert isinstance(exc.value.cause, ValueError)


def test_remote_timeout_error_preserved() -> None:
    timeout = RemoteTimeoutError("deadline exceeded", tool_name="external.capability")
    client = InMemoryRemoteClient(handler=InMemoryRemoteClient.raising_provider(timeout))
    adapter = RemoteToolExecutorAdapter(client)

    with pytest.raises(RemoteTimeoutError) as exc:
        adapter.execute(_remote_definition(), {})

    assert exc.value.tool_name == "external.capability"


def test_remote_provider_failure_response_mapped() -> None:
    client = InMemoryRemoteClient(
        handler=InMemoryRemoteClient.failing_provider("provider rejected request")
    )
    engine = create_tool_execution_engine(remote_client=client)

    with pytest.raises(RemoteProviderError) as exc:
        engine.execute(_remote_definition(), {"q": "x"})

    assert "provider rejected request" in str(exc.value)


def test_remote_response_validation() -> None:
    class InvalidResponseClient(RemoteToolClient):
        def send(self, request: ToolProviderRequest) -> ToolProviderResponse:
            return ToolProviderResponse(success=False, error="")  # type: ignore[arg-type]

    adapter = RemoteToolExecutorAdapter(InvalidResponseClient())

    with pytest.raises(RemoteResponseValidationError) as exc:
        adapter.execute(_remote_definition(), {})

    assert exc.value.tool_name == "external.capability"


def test_remote_response_validation_rejects_non_bool_success() -> None:
    class BadSuccessClient(RemoteToolClient):
        def send(self, request: ToolProviderRequest) -> Any:
            return ToolProviderResponse(success="yes")  # type: ignore[arg-type]

    adapter = RemoteToolExecutorAdapter(BadSuccessClient())

    with pytest.raises(RemoteResponseValidationError, match="success"):
        adapter.execute(_remote_definition(), {})


def test_remote_adapter_contains_no_business_logic() -> None:
    source_path = RemoteToolExecutorAdapter.execute.__code__.co_filename
    with open(source_path, encoding="utf-8") as handle:
        source = handle.read().lower()
    for forbidden in ("crm", "email", "search", "requests.", "httpx", "oauth"):
        assert forbidden not in source

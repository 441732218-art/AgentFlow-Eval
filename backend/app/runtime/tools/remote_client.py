# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Remote tool client abstraction — transport layer without HTTP binding."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from app.runtime.tools.provider import (
    ToolProviderProtocol,
    ToolProviderRequest,
    ToolProviderResponse,
)


class RemoteToolClient(ABC):
    """Send ``ToolProviderRequest`` payloads to an external provider."""

    @abstractmethod
    def send(self, request: ToolProviderRequest) -> ToolProviderResponse:
        """Deliver a request and return the provider response."""


class InMemoryRemoteClient(RemoteToolClient):
    """Test double that routes requests through an in-process provider."""

    def __init__(
        self,
        provider: ToolProviderProtocol | None = None,
        handler: Callable[[ToolProviderRequest], ToolProviderResponse] | None = None,
    ) -> None:
        if provider is not None and handler is not None:
            raise ValueError("Provide either provider or handler, not both")
        self._provider = provider
        self._handler = handler
        self.calls: list[ToolProviderRequest] = []

    def send(self, request: ToolProviderRequest) -> ToolProviderResponse:
        self.calls.append(request)
        if self._provider is not None:
            return self._provider.invoke(request)
        if self._handler is not None:
            return self._handler(request)
        return ToolProviderResponse(success=True, output={"stub": True})

    @staticmethod
    def failing_provider(message: str = "provider failure") -> Callable[[ToolProviderRequest], ToolProviderResponse]:
        """Build a handler that simulates a provider-side failure."""

        def _handler(_request: ToolProviderRequest) -> ToolProviderResponse:
            return ToolProviderResponse(success=False, error=message)

        return _handler

    @staticmethod
    def raising_provider(exc: Exception) -> Callable[[ToolProviderRequest], ToolProviderResponse]:
        """Build a handler that raises an exception (simulates transport failure)."""

        def _handler(_request: ToolProviderRequest) -> ToolProviderResponse:
            raise exc

        return _handler

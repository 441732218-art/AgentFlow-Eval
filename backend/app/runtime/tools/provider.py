# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool Provider Protocol — Runtime ↔ external provider contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolProviderRequest:
    """Payload sent from Runtime to an external tool provider."""

    tool_name: str
    arguments: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolProviderResponse:
    """Payload returned from an external tool provider to Runtime."""

    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolProviderProtocol(ABC):
    """Contract implemented by external tool providers (not Runtime)."""

    @abstractmethod
    def invoke(self, request: ToolProviderRequest) -> ToolProviderResponse:
        """Execute a remote tool capability and return a protocol response."""

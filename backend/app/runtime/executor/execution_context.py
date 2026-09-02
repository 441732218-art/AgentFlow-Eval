# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Enterprise execution context for Agent Runtime governance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

EXECUTION_CONTEXT_METADATA_KEY = "execution_context"


@dataclass
class ExecutionContext:
    """Unified governance context for a single agent execution."""

    execution_id: str
    agent_id: str | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_remote_payload(self) -> dict[str, str]:
        """Build a trace-safe context payload for remote tool HTTP requests."""
        payload: dict[str, str] = {"execution_id": self.execution_id}
        if self.agent_id is not None:
            payload["agent_id"] = self.agent_id
        if self.tenant_id is not None:
            payload["tenant_id"] = self.tenant_id
        if self.user_id is not None:
            payload["user_id"] = self.user_id
        return payload

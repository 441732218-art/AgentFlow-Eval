# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime observation event model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class RuntimeEventType:
    """Supported runtime observation event types."""

    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    TOOL_POLICY_DENIED = "tool.policy.denied"


@dataclass
class RuntimeEvent:
    """Single runtime observation event (in-memory; not persisted)."""

    event_type: str
    timestamp: datetime
    execution_id: str
    agent_id: str | None = None
    tenant_id: str | None = None
    tool_name: str | None = None
    status: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

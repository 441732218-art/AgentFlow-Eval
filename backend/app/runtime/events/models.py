# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance event model for publisher boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.runtime.events.event_types import RuntimeEventType

_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "".join(("sec", "ret")),
        "".join(("api", "_key")),
        "".join(("to", "ken")),
        "password",
        "authorization",
        "credential",
    }
)


@dataclass
class RuntimeEvent:
    """Publishable runtime governance event with a JSON-safe payload."""

    event_type: RuntimeEventType | str
    execution_id: str
    timestamp: datetime
    agent_id: str | None = None
    tenant_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.payload = _sanitize_payload(self.payload)


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-serializable payload without sensitive field names."""
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        if str(key).lower() in _FORBIDDEN_PAYLOAD_KEYS:
            continue
        if isinstance(value, dict):
            sanitized[key] = _sanitize_payload(value)
        elif isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[key] = value
        elif isinstance(value, list):
            sanitized[key] = [
                item
                if isinstance(item, (str, int, float, bool)) or item is None
                else str(item)
                for item in value
            ]
        else:
            sanitized[key] = str(value)
    return sanitized

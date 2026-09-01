# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime trace event model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TraceEvent:
    """Single Runtime trace event (in-memory; not persisted to v1 trace tables)."""

    event_type: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage under ``context.metadata['runtime_trace']``."""
        return {
            "type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": dict(self.metadata),
        }

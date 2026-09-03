# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime event stream publisher interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.event_stream.models import RuntimeEventEnvelope


class EventPublisher(Protocol):
    """Publishes runtime event stream envelopes to downstream consumers."""

    def publish(self, event: RuntimeEventEnvelope) -> None:
        """Publish one runtime event envelope."""

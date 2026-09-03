# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime event stream consumer interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.event_stream.models import RuntimeEventEnvelope


class EventConsumer(Protocol):
    """Consumes runtime event stream envelopes."""

    def consume(self, event: RuntimeEventEnvelope) -> None:
        """Handle one runtime event envelope."""

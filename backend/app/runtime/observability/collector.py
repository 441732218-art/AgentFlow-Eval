# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime observation collector."""

from __future__ import annotations

import threading
from typing import Protocol

from app.runtime.observability.events import RuntimeEvent


class ObservationCollector(Protocol):
    """Collects runtime observation events for a single execution scope."""

    def record(self, event: RuntimeEvent) -> None:
        """Record a runtime observation event."""

    def get_events(self) -> list[RuntimeEvent]:
        """Return all recorded events."""


class InMemoryObservationCollector:
    """Thread-safe in-memory observation store for tests and local runs."""

    def __init__(self) -> None:
        self._events: list[RuntimeEvent] = []
        self._lock = threading.Lock()

    def record(self, event: RuntimeEvent) -> None:
        with self._lock:
            self._events.append(event)

    def get_events(self) -> list[RuntimeEvent]:
        with self._lock:
            return list(self._events)

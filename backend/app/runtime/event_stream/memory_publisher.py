# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime event stream publisher."""

from __future__ import annotations

import threading

from app.runtime.event_stream.models import RuntimeEventEnvelope


class InMemoryEventPublisher:
    """Thread-safe in-memory event stream publisher."""

    def __init__(self) -> None:
        self._events: list[RuntimeEventEnvelope] = []
        self._lock = threading.Lock()

    def publish(self, event: RuntimeEventEnvelope) -> None:
        with self._lock:
            self._events.append(event)

    def get(self, event_id: str) -> RuntimeEventEnvelope | None:
        with self._lock:
            for event in self._events:
                if event.event_id == event_id:
                    return event
        return None

    def list(
        self,
        *,
        execution_id: str | None = None,
        event_type: str | None = None,
    ) -> list[RuntimeEventEnvelope]:
        with self._lock:
            records = list(self._events)
        if execution_id is not None:
            records = [record for record in records if record.execution_id == execution_id]
        if event_type is not None:
            records = [record for record in records if record.event_type == event_type]
        return records

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

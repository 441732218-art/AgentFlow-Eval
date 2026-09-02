# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime event publisher abstraction and in-memory implementation."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Protocol

from app.runtime.audit.models import audit_record_from_runtime_event
from app.runtime.events.models import RuntimeEvent

if TYPE_CHECKING:
    from app.runtime.audit.store import AuditEventStore

logger = logging.getLogger(__name__)


class RuntimeEventPublisher(Protocol):
    """Publishes runtime governance events to downstream consumers."""

    def publish(self, event: RuntimeEvent) -> None:
        """Publish a runtime event."""


class InMemoryEventPublisher:
    """Thread-safe in-memory publisher for tests and local wiring."""

    def __init__(self, audit_store: AuditEventStore | None = None) -> None:
        self._events: list[RuntimeEvent] = []
        self._lock = threading.Lock()
        self._audit_store = audit_store

    def publish(self, event: RuntimeEvent) -> None:
        with self._lock:
            self._events.append(event)

        if self._audit_store is not None:
            try:
                self._audit_store.append(audit_record_from_runtime_event(event))
            except Exception:
                logger.debug("runtime audit append failed", exc_info=True)

    def get_events(self) -> list[RuntimeEvent]:
        with self._lock:
            return list(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

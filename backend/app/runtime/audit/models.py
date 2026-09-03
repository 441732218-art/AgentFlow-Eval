# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Unified runtime audit record models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from app.runtime.events.event_types import RuntimeEventType
    from app.runtime.events.models import RuntimeEvent

AuditDecision = Literal["ALLOW", "DENY", "FAILED", "UNKNOWN"]
AuditSeverity = Literal["INFO", "WARNING", "ERROR"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AuditRecord:
    """Immutable unified audit record for runtime compliance boundaries."""

    audit_id: str
    event_type: str
    execution_id: str
    agent_id: str | None = None
    correlation_id: str | None = None
    actor: str | None = None
    action: str | None = None
    resource: str | None = None
    decision: AuditDecision = "UNKNOWN"
    severity: AuditSeverity = "INFO"
    timestamp: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Backward-compatible alias for Phase 9.7 audit consumers."""
        return self.audit_id

    @property
    def payload(self) -> dict[str, Any]:
        """Backward-compatible alias for Phase 9.7 audit consumers."""
        return self.metadata

    @property
    def tenant_id(self) -> str | None:
        """Optional tenant identifier stored in metadata."""
        value = self.metadata.get("tenant_id")
        return str(value) if value is not None else None

    def with_updates(self, **changes: Any) -> AuditRecord:
        """Return a new audit record with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)


def audit_record_from_runtime_event(event: RuntimeEvent) -> AuditRecord:
    """Convert a publishable runtime event into a unified audit record."""
    from app.runtime.events.event_types import RuntimeEventType

    event_type = (
        event.event_type.value
        if isinstance(event.event_type, RuntimeEventType)
        else str(event.event_type)
    )
    metadata = dict(event.payload)
    if event.tenant_id is not None:
        metadata.setdefault("tenant_id", event.tenant_id)

    decision: AuditDecision = "UNKNOWN"
    severity: AuditSeverity = "INFO"
    if "denied" in event_type:
        decision = "DENY"
        severity = "WARNING"
    elif "failed" in event_type:
        decision = "FAILED"
        severity = "ERROR"
    elif event_type.endswith(".completed") or event_type.endswith(".started"):
        decision = "ALLOW"

    return AuditRecord(
        audit_id=uuid.uuid4().hex,
        event_type=event_type,
        execution_id=event.execution_id,
        agent_id=event.agent_id,
        correlation_id=str(metadata.get("correlation_id"))
        if metadata.get("correlation_id") is not None
        else None,
        actor=event.agent_id,
        action=event_type,
        resource=str(metadata.get("tool_name")) if metadata.get("tool_name") else None,
        decision=decision,
        severity=severity,
        timestamp=event.timestamp,
        metadata=metadata,
    )

# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance evidence models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

from app.runtime.audit.models import AuditRecord

EvidenceStatus = Literal["COMPLETED", "FAILED", "RUNNING", "UNKNOWN"]
PermissionDecisionValue = Literal["ALLOW", "DENY", "UNKNOWN"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class StateSnapshotSummary:
    """Immutable summary of execution state for evidence aggregation."""

    execution_id: str
    agent_id: str
    plan_id: str
    status: str
    current_step: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckpointSummary:
    """Immutable summary of the latest execution checkpoint."""

    checkpoint_id: str
    execution_id: str
    plan_id: str | None = None
    step_id: str | None = None
    status: str | None = None
    completed_steps: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemorySnapshotSummary:
    """Immutable summary of runtime memory context."""

    memory_id: str
    execution_id: str
    agent_id: str
    namespace: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EventSummary:
    """Immutable summary of runtime event stream activity."""

    total_events: int
    event_types: tuple[str, ...] = ()
    first_event_id: str | None = None
    last_event_id: str | None = None


@dataclass(frozen=True)
class MetricsSummary:
    """Immutable summary of execution analytics metrics."""

    duration_ms: int | None = None
    step_count: int = 0
    tool_count: int = 0
    failure_count: int = 0
    status: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PermissionDecision:
    """Immutable permission decision captured for governance evidence."""

    execution_id: str
    decision: PermissionDecisionValue
    tool_name: str | None = None
    permission: str | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionEvidence:
    """Immutable aggregated governance evidence for one agent execution."""

    evidence_id: str
    execution_id: str
    agent_id: str
    correlation_id: str | None
    status: EvidenceStatus
    state_snapshot: StateSnapshotSummary | None = None
    checkpoint_summary: CheckpointSummary | None = None
    memory_snapshot: MemorySnapshotSummary | None = None
    audit_records: tuple[AuditRecord, ...] = ()
    event_summary: EventSummary | None = None
    metrics_summary: MetricsSummary | None = None
    permission_decisions: tuple[PermissionDecision, ...] = ()
    created_at: datetime = field(default_factory=_utc_now)

    def with_updates(self, **changes: Any) -> ExecutionEvidence:
        """Return a new evidence record with updated fields."""
        if "audit_records" in changes:
            changes["audit_records"] = tuple(changes["audit_records"])
        if "permission_decisions" in changes:
            changes["permission_decisions"] = tuple(changes["permission_decisions"])
        return replace(self, **changes)

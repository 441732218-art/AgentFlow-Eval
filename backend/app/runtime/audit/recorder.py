# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime audit recording coordinator."""

from __future__ import annotations

import uuid
from typing import Any

from app.runtime.audit.models import AuditDecision, AuditRecord, AuditSeverity
from app.runtime.audit.store import AuditStore


class RuntimeAuditRecorder:
    """Convert runtime lifecycle signals into unified audit records."""

    def __init__(self, store: AuditStore) -> None:
        self._store = store

    @property
    def store(self) -> AuditStore:
        return self._store

    def record_execution_event(
        self,
        *,
        event_type: str,
        execution_id: str,
        agent_id: str | None = None,
        correlation_id: str | None = None,
        actor: str | None = None,
        action: str | None = None,
        resource: str | None = None,
        decision: AuditDecision = "ALLOW",
        severity: AuditSeverity = "INFO",
        metadata: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Record an execution lifecycle audit event."""
        return self._record(
            event_type=event_type,
            execution_id=execution_id,
            agent_id=agent_id,
            correlation_id=correlation_id,
            actor=actor,
            action=action or event_type,
            resource=resource,
            decision=decision,
            severity=severity,
            metadata=metadata,
        )

    def record_permission_event(
        self,
        *,
        event_type: str,
        execution_id: str,
        agent_id: str | None = None,
        correlation_id: str | None = None,
        actor: str | None = None,
        resource: str | None = None,
        decision: AuditDecision = "DENY",
        severity: AuditSeverity = "WARNING",
        metadata: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Record a permission decision audit event."""
        return self._record(
            event_type=event_type,
            execution_id=execution_id,
            agent_id=agent_id,
            correlation_id=correlation_id,
            actor=actor or agent_id,
            action="tool.permission.evaluate",
            resource=resource,
            decision=decision,
            severity=severity,
            metadata=metadata,
        )

    def record_governance_event(
        self,
        *,
        event_type: str,
        execution_id: str,
        agent_id: str | None = None,
        correlation_id: str | None = None,
        actor: str | None = None,
        action: str | None = None,
        resource: str | None = None,
        decision: AuditDecision = "UNKNOWN",
        severity: AuditSeverity = "INFO",
        metadata: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Record a governance lifecycle audit event."""
        return self._record(
            event_type=event_type,
            execution_id=execution_id,
            agent_id=agent_id,
            correlation_id=correlation_id,
            actor=actor or agent_id,
            action=action or event_type,
            resource=resource,
            decision=decision,
            severity=severity,
            metadata=metadata,
        )

    def record_failure_event(
        self,
        *,
        event_type: str,
        execution_id: str,
        agent_id: str | None = None,
        correlation_id: str | None = None,
        actor: str | None = None,
        action: str | None = None,
        resource: str | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Record a runtime failure audit event."""
        payload = dict(metadata or {})
        if error is not None:
            payload["error"] = error
        return self._record(
            event_type=event_type,
            execution_id=execution_id,
            agent_id=agent_id,
            correlation_id=correlation_id,
            actor=actor or agent_id,
            action=action or event_type,
            resource=resource,
            decision="FAILED",
            severity="ERROR",
            metadata=payload,
        )

    def _record(
        self,
        *,
        event_type: str,
        execution_id: str,
        agent_id: str | None,
        correlation_id: str | None,
        actor: str | None,
        action: str | None,
        resource: str | None,
        decision: AuditDecision,
        severity: AuditSeverity,
        metadata: dict[str, Any] | None,
    ) -> AuditRecord:
        record = AuditRecord(
            audit_id=uuid.uuid4().hex,
            event_type=event_type,
            execution_id=execution_id,
            agent_id=agent_id,
            correlation_id=correlation_id,
            actor=actor,
            action=action,
            resource=resource,
            decision=decision,
            severity=severity,
            metadata=dict(metadata or {}),
        )
        self._store.record(record)
        return record

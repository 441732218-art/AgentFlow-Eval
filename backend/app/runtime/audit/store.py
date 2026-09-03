# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime audit store interfaces."""

from __future__ import annotations

from typing import Protocol

from app.runtime.audit.models import AuditRecord


class AuditStore(Protocol):
    """Persists unified runtime audit records."""

    def record(self, record: AuditRecord) -> None:
        """Persist an audit record."""

    def get(self, audit_id: str) -> AuditRecord | None:
        """Return one audit record by id."""

    def list_by_execution(self, execution_id: str) -> list[AuditRecord]:
        """Return audit records for an execution."""

    def list_by_agent(self, agent_id: str) -> list[AuditRecord]:
        """Return audit records for an agent."""

    def delete(self, audit_id: str) -> None:
        """Delete one audit record by id."""


class AuditEventStore(Protocol):
    """Legacy audit store interface used by governance event publishing."""

    def append(self, record: AuditRecord) -> None:
        """Append an audit record."""

    def query(
        self,
        execution_id: str | None = None,
        tenant_id: str | None = None,
    ) -> list[AuditRecord]:
        """Query audit records with optional filters."""

    def clear(self) -> None:
        """Remove all stored audit records."""

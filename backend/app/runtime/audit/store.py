# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Audit store interface for runtime governance queries."""

from __future__ import annotations

from typing import Protocol

from app.runtime.audit.models import AuditRecord


class AuditEventStore(Protocol):
    """Persists runtime audit records for governance queries."""

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

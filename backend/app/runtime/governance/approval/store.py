# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance approval store interface."""

from __future__ import annotations

from typing import Protocol

from app.runtime.governance.approval.models import ApprovalDecision, ApprovalRequest


class ApprovalStore(Protocol):
    """Persists governance approval requests and decisions."""

    def create(self, request: ApprovalRequest) -> None:
        """Create or replace an approval request."""

    def get(self, request_id: str) -> ApprovalRequest | None:
        """Return one approval request by id."""

    def update(self, request: ApprovalRequest) -> None:
        """Replace an existing approval request."""

    def list_pending(self) -> list[ApprovalRequest]:
        """Return all pending approval requests."""

    def record_decision(self, decision: ApprovalDecision) -> None:
        """Record an approval decision and update request status."""

    def get_decisions(self, request_id: str) -> list[ApprovalDecision]:
        """Return decision history for one approval request."""

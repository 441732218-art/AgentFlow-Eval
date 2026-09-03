# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance approval workflow models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

ApprovalRequestStatus = Literal["PENDING", "APPROVED", "REJECTED", "EXPIRED"]
ApprovalDecisionValue = Literal["APPROVE", "REJECT"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ApprovalRequest:
    """Immutable governance approval request."""

    request_id: str
    execution_id: str
    reason: str
    status: ApprovalRequestStatus = "PENDING"
    policy_id: str | None = None
    decision_id: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> ApprovalRequest:
        """Return a new approval request with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        if "updated_at" not in changes:
            changes["updated_at"] = _utc_now()
        return replace(self, **changes)


@dataclass(frozen=True)
class ApprovalDecision:
    """Immutable approval decision recorded for a request."""

    request_id: str
    decision: ApprovalDecisionValue
    approver: str
    reason: str
    timestamp: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **changes: Any) -> ApprovalDecision:
        """Return a new approval decision with updated fields."""
        if "metadata" in changes:
            changes["metadata"] = dict(changes["metadata"])
        return replace(self, **changes)

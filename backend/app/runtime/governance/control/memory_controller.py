# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime governance controller."""

from __future__ import annotations

import threading
import uuid
from typing import Any

from app.runtime.governance.control.controller import GovernanceController
from app.runtime.governance.control.models import (
    GovernanceControlActionType,
    GovernanceControlDecision,
    GovernanceControlDecisionStatus,
)
from app.runtime.governance.models import GovernanceDecision, GovernanceDecisionStatus

_CONTROL_STATUS_BY_DECISION: dict[GovernanceDecisionStatus, GovernanceControlDecisionStatus] = {
    "ALLOW": "ALLOW",
    "WARN": "WARN",
    "DENY": "BLOCK",
}

_ACTION_TYPE_BY_DECISION: dict[GovernanceDecisionStatus, GovernanceControlActionType] = {
    "ALLOW": "ALLOW",
    "WARN": "WARN",
    "DENY": "BLOCK",
}


class InMemoryGovernanceController:
    """Thread-safe in-memory governance control bridge."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._decisions: list[GovernanceControlDecision] = []
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable control evaluation."""
        with self._lock:
            self._enabled = enabled

    def evaluate(self, decision: GovernanceDecision) -> GovernanceControlDecision:
        """Translate a governance decision into a control decision."""
        with self._lock:
            if not self._enabled:
                control_decision = self._build_disabled_decision(decision)
            else:
                control_decision = self._build_decision(decision)
            self._decisions.append(control_decision)
            return control_decision

    def list_decisions(
        self,
        *,
        execution_id: str | None = None,
    ) -> list[GovernanceControlDecision]:
        """Return recorded control decisions."""
        with self._lock:
            records = list(self._decisions)
        if execution_id is not None:
            records = [
                record for record in records if record.execution_id == execution_id
            ]
        return records

    def clear(self) -> None:
        """Remove all recorded control decisions."""
        with self._lock:
            self._decisions.clear()

    def _build_decision(self, decision: GovernanceDecision) -> GovernanceControlDecision:
        decision_status = _CONTROL_STATUS_BY_DECISION.get(decision.status)
        action_type = _ACTION_TYPE_BY_DECISION.get(decision.status)
        if decision_status is None or action_type is None:
            raise ValueError(f"Unsupported governance decision status: {decision.status}")

        return GovernanceControlDecision(
            control_id=uuid.uuid4().hex,
            execution_id=decision.execution_id,
            decision_status=decision_status,
            action_type=action_type,
            reason=_format_reason(decision),
            metadata=_build_metadata(decision),
        )

    def _build_disabled_decision(
        self,
        decision: GovernanceDecision,
    ) -> GovernanceControlDecision:
        metadata = _build_metadata(decision)
        metadata["control_enabled"] = False
        return GovernanceControlDecision(
            control_id=uuid.uuid4().hex,
            execution_id=decision.execution_id,
            decision_status="ALLOW",
            action_type="ALLOW",
            reason="control evaluation disabled",
            metadata=metadata,
        )


def _format_reason(decision: GovernanceDecision) -> str:
    if decision.reasons:
        return "; ".join(decision.reasons)
    return f"governance decision {decision.status.lower()}"


def _build_metadata(decision: GovernanceDecision) -> dict[str, Any]:
    metadata = {
        "decision_id": decision.decision_id,
        "agent_id": decision.agent_id,
        "source_decision_status": decision.status,
        "evaluated_at": decision.evaluated_at.isoformat(),
    }
    if decision.metadata:
        metadata.update(dict(decision.metadata))
    return metadata

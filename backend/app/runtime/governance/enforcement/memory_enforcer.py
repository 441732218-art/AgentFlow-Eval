# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime governance enforcer."""

from __future__ import annotations

import threading
import uuid
from typing import Any

from app.runtime.governance.enforcement.enforcer import GovernanceEnforcer
from app.runtime.governance.enforcement.models import GovernanceAction, GovernanceActionType
from app.runtime.governance.models import GovernanceDecision, GovernanceDecisionStatus

_ACTION_TYPE_BY_STATUS: dict[GovernanceDecisionStatus, GovernanceActionType] = {
    "ALLOW": "ALLOW",
    "WARN": "WARN",
    "DENY": "BLOCK",
}


class InMemoryGovernanceEnforcer:
    """Thread-safe in-memory governance enforcement bridge."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._actions: list[GovernanceAction] = []
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable enforcement translation."""
        with self._lock:
            self._enabled = enabled

    def enforce(self, decision: GovernanceDecision) -> GovernanceAction:
        """Translate a governance decision into an enforcement action."""
        with self._lock:
            if not self._enabled:
                action = self._build_disabled_action(decision)
            else:
                action = self._build_action(decision)
            self._actions.append(action)
            return action

    def list_actions(
        self,
        *,
        execution_id: str | None = None,
    ) -> list[GovernanceAction]:
        """Return recorded enforcement actions."""
        with self._lock:
            records = list(self._actions)
        if execution_id is not None:
            records = [record for record in records if record.execution_id == execution_id]
        return records

    def clear(self) -> None:
        """Remove all recorded enforcement actions."""
        with self._lock:
            self._actions.clear()

    def _build_action(self, decision: GovernanceDecision) -> GovernanceAction:
        action_type = _ACTION_TYPE_BY_STATUS.get(decision.status)
        if action_type is None:
            raise ValueError(f"Unsupported governance decision status: {decision.status}")

        return GovernanceAction(
            action_id=uuid.uuid4().hex,
            execution_id=decision.execution_id,
            decision_status=decision.status,
            action_type=action_type,
            reason=_format_reason(decision),
            metadata=_build_metadata(decision),
        )

    def _build_disabled_action(self, decision: GovernanceDecision) -> GovernanceAction:
        metadata = _build_metadata(decision)
        metadata["enforcement_enabled"] = False
        return GovernanceAction(
            action_id=uuid.uuid4().hex,
            execution_id=decision.execution_id,
            decision_status=decision.status,
            action_type="ALLOW",
            reason="enforcement disabled",
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
        "evaluated_at": decision.evaluated_at.isoformat(),
    }
    if decision.metadata:
        metadata.update(dict(decision.metadata))
    return metadata

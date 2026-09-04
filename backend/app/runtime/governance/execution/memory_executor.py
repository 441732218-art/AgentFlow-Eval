# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory governance execution contract."""

from __future__ import annotations

import threading
from typing import Any

from app.runtime.governance.execution.models import (
    GovernanceExecutionActionType,
    GovernanceExecutionEffect,
    GovernanceExecutionRecord,
)

_ALLOWED_ACTION_TYPES: frozenset[GovernanceExecutionActionType] = frozenset(
    {"ALLOW", "WARN", "BLOCK", "REQUIRE_APPROVAL"}
)


class InMemoryGovernanceExecutionContract:
    """Thread-safe in-memory governance execution contract."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._executions: dict[str, GovernanceExecutionRecord] = {}
        self._history: list[GovernanceExecutionRecord] = []
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable governance execution observation."""
        with self._lock:
            self._enabled = enabled

    def execute(self, effect: GovernanceExecutionEffect) -> GovernanceExecutionRecord:
        """Observe one governance execution effect without runtime modification."""
        with self._lock:
            if not self._enabled:
                record = _build_disabled_record(effect)
            else:
                record = _build_record(effect)
            self._executions[effect.effect_id] = record
            self._history.append(record)
            return record

    def get_execution(self, effect_id: str) -> GovernanceExecutionRecord | None:
        """Return one recorded governance execution by effect identifier."""
        with self._lock:
            return self._executions.get(effect_id)

    def list_executions(self) -> list[GovernanceExecutionRecord]:
        """Return all recorded governance executions."""
        with self._lock:
            records = list(self._history)
        return sorted(records, key=lambda record: record.executed_at)

    def clear(self) -> None:
        """Remove all recorded governance executions."""
        with self._lock:
            self._executions.clear()
            self._history.clear()


def _build_record(effect: GovernanceExecutionEffect) -> GovernanceExecutionRecord:
    if effect.action_type not in _ALLOWED_ACTION_TYPES:
        raise ValueError(f"Unsupported governance execution action type: {effect.action_type}")

    metadata = _build_metadata(effect, applied=True)
    return GovernanceExecutionRecord(
        effect_id=effect.effect_id,
        decision_id=effect.decision_id,
        action_type=effect.action_type,
        target=effect.target,
        reason=effect.reason,
        evidence_reference=effect.evidence_reference,
        applied=True,
        metadata=metadata,
    )


def _build_disabled_record(effect: GovernanceExecutionEffect) -> GovernanceExecutionRecord:
    metadata = _build_metadata(effect, applied=False)
    metadata["execution_enabled"] = False
    return GovernanceExecutionRecord(
        effect_id=effect.effect_id,
        decision_id=effect.decision_id,
        action_type="ALLOW",
        target=effect.target,
        reason="governance execution contract disabled",
        evidence_reference=effect.evidence_reference,
        applied=False,
        metadata=metadata,
    )


def _build_metadata(effect: GovernanceExecutionEffect, *, applied: bool) -> dict[str, Any]:
    metadata = {
        "observation_only": True,
        "execution_applied": applied,
        **dict(effect.metadata),
    }
    return metadata

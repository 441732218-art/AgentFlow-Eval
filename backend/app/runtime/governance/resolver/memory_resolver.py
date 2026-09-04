# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory governance effect resolver."""

from __future__ import annotations

import threading
import uuid
from typing import Any

from app.runtime.governance.execution.models import (
    GovernanceExecutionActionType,
    GovernanceExecutionEffect,
)
from app.runtime.governance.resolver.models import (
    GovernanceEffectResolution,
    GovernanceEffectResolutionType,
)

_RESOLUTION_BY_ACTION: dict[GovernanceExecutionActionType, GovernanceEffectResolutionType] = {
    "ALLOW": "CONTINUE",
    "WARN": "CONTINUE_WITH_WARNING",
    "BLOCK": "BLOCK_REQUEST",
    "REQUIRE_APPROVAL": "WAIT_APPROVAL",
}

_EXECUTABLE_BY_RESOLUTION: dict[GovernanceEffectResolutionType, bool] = {
    "CONTINUE": True,
    "CONTINUE_WITH_WARNING": True,
    "BLOCK_REQUEST": False,
    "WAIT_APPROVAL": False,
}


class InMemoryGovernanceEffectResolver:
    """Thread-safe in-memory governance effect resolver."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._resolutions: dict[str, GovernanceEffectResolution] = {}
        self._history: list[GovernanceEffectResolution] = []
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable effect resolution."""
        with self._lock:
            self._enabled = enabled

    def resolve(self, effect: GovernanceExecutionEffect) -> GovernanceEffectResolution:
        """Resolve one governance execution effect without runtime execution."""
        with self._lock:
            if not self._enabled:
                resolution = _build_disabled_resolution(effect)
            else:
                resolution = _build_resolution(effect)
            self._resolutions[resolution.resolution_id] = resolution
            self._history.append(resolution)
            return resolution

    def get_resolution(self, resolution_id: str) -> GovernanceEffectResolution | None:
        """Return one recorded resolution by identifier."""
        with self._lock:
            return self._resolutions.get(resolution_id)

    def list_resolutions(self) -> list[GovernanceEffectResolution]:
        """Return all recorded effect resolutions."""
        with self._lock:
            records = list(self._history)
        return records

    def clear(self) -> None:
        """Remove all recorded effect resolutions."""
        with self._lock:
            self._resolutions.clear()
            self._history.clear()


def _build_resolution(effect: GovernanceExecutionEffect) -> GovernanceEffectResolution:
    resolution_type = _RESOLUTION_BY_ACTION.get(effect.action_type)
    if resolution_type is None:
        raise ValueError(f"Unsupported governance execution action type: {effect.action_type}")

    return GovernanceEffectResolution(
        resolution_id=uuid.uuid4().hex,
        effect_id=effect.effect_id,
        resolution_type=resolution_type,
        executable=_EXECUTABLE_BY_RESOLUTION[resolution_type],
        reason=effect.reason,
        metadata=_build_metadata(effect, resolution_type=resolution_type),
    )


def _build_disabled_resolution(
    effect: GovernanceExecutionEffect,
) -> GovernanceEffectResolution:
    metadata = _build_metadata(effect, resolution_type="CONTINUE")
    metadata["resolver_enabled"] = False
    return GovernanceEffectResolution(
        resolution_id=uuid.uuid4().hex,
        effect_id=effect.effect_id,
        resolution_type="CONTINUE",
        executable=True,
        reason="governance effect resolver disabled",
        metadata=metadata,
    )


def _build_metadata(
    effect: GovernanceExecutionEffect,
    *,
    resolution_type: GovernanceEffectResolutionType,
) -> dict[str, Any]:
    return {
        "decision_id": effect.decision_id,
        "action_type": effect.action_type,
        "target": effect.target,
        "evidence_reference": effect.evidence_reference,
        "resolution_type": resolution_type,
        "observation_only": True,
        **dict(effect.metadata),
    }

# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory governance runtime decision adapter."""

from __future__ import annotations

import threading
import uuid
from typing import Any

from app.runtime.governance.execution.models import GovernanceExecutionActionType, GovernanceExecutionEffect
from app.runtime.governance.resolver.models import GovernanceEffectResolutionType
from app.runtime.governance.runtime_adapter.models import (
    GovernanceRuntimeDecisionRequest,
    GovernanceRuntimeDecisionResult,
    GovernanceRuntimeDecisionStatus,
)

_EFFECT_ACTION_BY_DECISION: dict[GovernanceRuntimeDecisionStatus, GovernanceExecutionActionType] = {
    "ALLOW": "ALLOW",
    "WARN": "WARN",
    "DENY": "BLOCK",
    "BLOCK": "BLOCK",
    "REQUIRE_APPROVAL": "REQUIRE_APPROVAL",
}

_RESOLUTION_BY_EFFECT: dict[GovernanceExecutionActionType, GovernanceEffectResolutionType] = {
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


class InMemoryGovernanceRuntimeDecisionAdapter:
    """Thread-safe in-memory governance runtime decision adapter."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._results: dict[str, GovernanceRuntimeDecisionResult] = {}
        self._history: list[GovernanceRuntimeDecisionResult] = []
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable governance decision adaptation."""
        with self._lock:
            self._enabled = enabled

    def adapt(self, request: GovernanceRuntimeDecisionRequest) -> GovernanceRuntimeDecisionResult:
        """Adapt one governance decision without runtime execution."""
        with self._lock:
            if not self._enabled:
                result = _build_disabled_result(request)
            else:
                result = _build_result(request)
            self._results[result.result_id] = result
            self._history.append(result)
            return result

    def get_result(self, result_id: str) -> GovernanceRuntimeDecisionResult | None:
        """Return one recorded adaptation result."""
        with self._lock:
            return self._results.get(result_id)

    def list_results(self) -> list[GovernanceRuntimeDecisionResult]:
        """Return all recorded adaptation results."""
        with self._lock:
            records = list(self._history)
        return records

    def clear(self) -> None:
        """Remove all recorded adaptation results."""
        with self._lock:
            self._results.clear()
            self._history.clear()


def _build_result(request: GovernanceRuntimeDecisionRequest) -> GovernanceRuntimeDecisionResult:
    effect_action = _EFFECT_ACTION_BY_DECISION.get(request.decision_status)
    if effect_action is None:
        raise ValueError(f"Unsupported governance decision status: {request.decision_status}")

    resolution_type = _RESOLUTION_BY_EFFECT[effect_action]
    effect = GovernanceExecutionEffect(
        effect_id=uuid.uuid4().hex,
        decision_id=request.decision_id,
        action_type=effect_action,
        target=request.target,
        reason=request.reason,
        evidence_reference=request.evidence_reference,
        metadata=_build_effect_metadata(request, effect_action=effect_action),
    )
    return GovernanceRuntimeDecisionResult(
        result_id=uuid.uuid4().hex,
        decision_id=request.decision_id,
        execution_id=request.execution_id,
        effect=effect,
        effect_action_type=effect_action,
        resolution_type=resolution_type,
        executable=_EXECUTABLE_BY_RESOLUTION[resolution_type],
        metadata=_build_result_metadata(
            request,
            effect_action=effect_action,
            resolution_type=resolution_type,
        ),
    )


def _build_disabled_result(
    request: GovernanceRuntimeDecisionRequest,
) -> GovernanceRuntimeDecisionResult:
    effect = GovernanceExecutionEffect(
        effect_id=uuid.uuid4().hex,
        decision_id=request.decision_id,
        action_type="ALLOW",
        target=request.target,
        reason="governance runtime decision adapter disabled",
        evidence_reference=request.evidence_reference,
        metadata=_build_effect_metadata(request, effect_action="ALLOW", adapter_enabled=False),
    )
    return GovernanceRuntimeDecisionResult(
        result_id=uuid.uuid4().hex,
        decision_id=request.decision_id,
        execution_id=request.execution_id,
        effect=effect,
        effect_action_type="ALLOW",
        resolution_type="CONTINUE",
        executable=True,
        metadata=_build_result_metadata(
            request,
            effect_action="ALLOW",
            resolution_type="CONTINUE",
            adapter_enabled=False,
        ),
    )


def _build_effect_metadata(
    request: GovernanceRuntimeDecisionRequest,
    *,
    effect_action: GovernanceExecutionActionType,
    adapter_enabled: bool = True,
) -> dict[str, Any]:
    metadata = {
        "execution_id": request.execution_id,
        "decision_status": request.decision_status,
        "effect_action_type": effect_action,
        "observation_only": True,
        **dict(request.metadata),
    }
    if request.agent_id is not None:
        metadata["agent_id"] = request.agent_id
    if not adapter_enabled:
        metadata["adapter_enabled"] = False
    return metadata


def _build_result_metadata(
    request: GovernanceRuntimeDecisionRequest,
    *,
    effect_action: GovernanceExecutionActionType,
    resolution_type: GovernanceEffectResolutionType,
    adapter_enabled: bool = True,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "decision_status": request.decision_status,
        "effect_action_type": effect_action,
        "resolution_type": resolution_type,
        "target": request.target,
        "observation_only": True,
        **dict(request.metadata),
    }
    if request.agent_id is not None:
        metadata["agent_id"] = request.agent_id
    if not adapter_enabled:
        metadata["adapter_enabled"] = False
    return metadata

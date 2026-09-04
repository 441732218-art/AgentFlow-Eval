# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime governance decision gateway."""

from __future__ import annotations

import threading
import uuid
from typing import Any

from app.runtime.governance.control.models import GovernanceControlDecisionStatus
from app.runtime.governance.gateway.gateway import GovernanceDecisionGateway
from app.runtime.governance.gateway.models import (
    GovernanceGateRequest,
    GovernanceGateResult,
    GovernanceGateStatus,
)

_GATE_STATUS_BY_CONTROL: dict[GovernanceControlDecisionStatus, GovernanceGateStatus] = {
    "ALLOW": "ALLOW",
    "WARN": "WARN",
    "BLOCK": "BLOCK",
    "REQUIRE_APPROVAL": "REQUIRE_APPROVAL",
}


class InMemoryGovernanceDecisionGateway:
    """Thread-safe in-memory governance decision gateway."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._results: list[GovernanceGateResult] = []
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable gateway evaluation."""
        with self._lock:
            self._enabled = enabled

    def evaluate(self, request: GovernanceGateRequest) -> GovernanceGateResult:
        """Evaluate a governance control outcome and return a gate result."""
        with self._lock:
            if not self._enabled:
                result = self._build_disabled_result(request)
            else:
                result = self._build_result(request)
            self._results.append(result)
            return result

    def list_results(
        self,
        *,
        execution_id: str | None = None,
    ) -> list[GovernanceGateResult]:
        """Return recorded gateway results."""
        with self._lock:
            records = list(self._results)
        if execution_id is not None:
            records = [
                record for record in records if record.execution_id == execution_id
            ]
        return records

    def clear(self) -> None:
        """Remove all recorded gateway results."""
        with self._lock:
            self._results.clear()

    def _build_result(self, request: GovernanceGateRequest) -> GovernanceGateResult:
        status = _GATE_STATUS_BY_CONTROL.get(request.control_decision.decision_status)
        if status is None:
            raise ValueError(
                "Unsupported governance control decision status: "
                f"{request.control_decision.decision_status}"
            )

        return GovernanceGateResult(
            gate_id=uuid.uuid4().hex,
            execution_id=request.execution_id,
            status=status,
            reason=request.control_decision.reason,
            metadata=_build_metadata(request, status=status),
        )

    def _build_disabled_result(self, request: GovernanceGateRequest) -> GovernanceGateResult:
        metadata = _build_metadata(request, status="ALLOW")
        metadata["gateway_enabled"] = False
        return GovernanceGateResult(
            gate_id=uuid.uuid4().hex,
            execution_id=request.execution_id,
            status="ALLOW",
            reason="gateway evaluation disabled",
            metadata=metadata,
        )


def _build_metadata(
    request: GovernanceGateRequest,
    *,
    status: GovernanceGateStatus,
) -> dict[str, Any]:
    metadata = {
        "agent_id": request.agent_id,
        "tool_name": request.tool_name,
        "decision_id": request.decision_id,
        "control_id": request.control_decision.control_id,
        "control_status": request.control_decision.decision_status,
        "control_action_type": request.control_decision.action_type,
        "gate_status": status,
    }
    if request.metadata:
        metadata.update(dict(request.metadata))
    if request.control_decision.metadata:
        metadata.update(
            {
                key: value
                for key, value in request.control_decision.metadata.items()
                if key not in metadata
            }
        )
    return metadata

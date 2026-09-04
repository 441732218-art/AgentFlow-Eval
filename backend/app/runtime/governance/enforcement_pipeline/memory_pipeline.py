# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime enforcement pipeline."""

from __future__ import annotations

import threading
import uuid
from typing import Any

from app.runtime.governance.enforcement_pipeline.models import (
    EnforcementRequest,
    EnforcementResult,
    EnforcementStatus,
)
from app.runtime.governance.enforcement_pipeline.pipeline import RuntimeEnforcementPipeline
from app.runtime.governance.gateway.models import GovernanceGateStatus

_ENFORCEMENT_STATUS_BY_GATE: dict[GovernanceGateStatus, EnforcementStatus] = {
    "ALLOW": "ALLOW",
    "WARN": "WARN",
    "BLOCK": "BLOCK",
    "REQUIRE_APPROVAL": "PENDING_APPROVAL",
}


class InMemoryRuntimeEnforcementPipeline:
    """Thread-safe in-memory runtime enforcement pipeline."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._results: list[EnforcementResult] = []
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable enforcement pipeline evaluation."""
        with self._lock:
            self._enabled = enabled

    def evaluate(self, request: EnforcementRequest) -> EnforcementResult:
        """Evaluate a gateway result and return an enforcement result."""
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
    ) -> list[EnforcementResult]:
        """Return recorded enforcement results."""
        with self._lock:
            records = list(self._results)
        if execution_id is not None:
            records = [
                record for record in records if record.execution_id == execution_id
            ]
        return records

    def clear(self) -> None:
        """Remove all recorded enforcement results."""
        with self._lock:
            self._results.clear()

    def _build_result(self, request: EnforcementRequest) -> EnforcementResult:
        status = _ENFORCEMENT_STATUS_BY_GATE.get(request.gate_result.status)
        if status is None:
            raise ValueError(
                f"Unsupported governance gate status: {request.gate_result.status}"
            )

        return EnforcementResult(
            enforcement_id=uuid.uuid4().hex,
            execution_id=request.execution_id,
            status=status,
            reason=request.gate_result.reason,
            metadata=_build_metadata(request, status=status),
        )

    def _build_disabled_result(self, request: EnforcementRequest) -> EnforcementResult:
        metadata = _build_metadata(request, status="ALLOW")
        metadata["enforcement_enabled"] = False
        return EnforcementResult(
            enforcement_id=uuid.uuid4().hex,
            execution_id=request.execution_id,
            status="ALLOW",
            reason="enforcement pipeline disabled",
            metadata=metadata,
        )


def _build_metadata(
    request: EnforcementRequest,
    *,
    status: EnforcementStatus,
) -> dict[str, Any]:
    metadata = {
        "gate_id": request.gate_result.gate_id,
        "gate_status": request.gate_result.status,
        "enforcement_status": status,
    }
    if request.context:
        metadata["context"] = dict(request.context)
    if request.metadata:
        metadata.update(dict(request.metadata))
    if request.gate_result.metadata:
        metadata.update(
            {
                key: value
                for key, value in request.gate_result.metadata.items()
                if key not in metadata
            }
        )
    return metadata

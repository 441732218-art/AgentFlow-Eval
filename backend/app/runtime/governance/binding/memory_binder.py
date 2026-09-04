# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime enforcement binder."""

from __future__ import annotations

import threading
import uuid
from typing import Any

from app.runtime.governance.binding.binder import RuntimeEnforcementBinder
from app.runtime.governance.binding.models import (
    RuntimeBindingDecision,
    RuntimeBindingRequest,
    RuntimeBindingResult,
)
from app.runtime.governance.enforcement_pipeline.models import EnforcementStatus

_BINDING_DECISION_BY_ENFORCEMENT: dict[EnforcementStatus, RuntimeBindingDecision] = {
    "ALLOW": "ALLOW",
    "WARN": "WARN",
    "BLOCK": "BLOCK",
    "PENDING_APPROVAL": "PENDING_APPROVAL",
}


class InMemoryRuntimeEnforcementBinder:
    """Thread-safe in-memory runtime enforcement binder."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._bindings: list[RuntimeBindingResult] = []
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable enforcement binding."""
        with self._lock:
            self._enabled = enabled

    def bind(self, request: RuntimeBindingRequest) -> RuntimeBindingResult:
        """Bind an enforcement result to a runtime observation record."""
        with self._lock:
            if not self._enabled:
                result = self._build_disabled_result(request)
            else:
                result = self._build_result(request)
            self._bindings.append(result)
            return result

    def list_bindings(
        self,
        *,
        execution_id: str | None = None,
    ) -> list[RuntimeBindingResult]:
        """Return recorded binding results."""
        with self._lock:
            records = list(self._bindings)
        if execution_id is not None:
            records = [
                record for record in records if record.execution_id == execution_id
            ]
        return records

    def clear(self) -> None:
        """Remove all recorded binding results."""
        with self._lock:
            self._bindings.clear()

    def _build_result(self, request: RuntimeBindingRequest) -> RuntimeBindingResult:
        decision = _BINDING_DECISION_BY_ENFORCEMENT.get(request.enforcement_result.status)
        if decision is None:
            raise ValueError(
                "Unsupported enforcement result status: "
                f"{request.enforcement_result.status}"
            )

        return RuntimeBindingResult(
            binding_id=uuid.uuid4().hex,
            execution_id=request.execution_id,
            decision=decision,
            applied=True,
            reason=request.enforcement_result.reason,
            metadata=_build_metadata(request, decision=decision),
        )

    def _build_disabled_result(self, request: RuntimeBindingRequest) -> RuntimeBindingResult:
        metadata = _build_metadata(request, decision="ALLOW")
        metadata["binding_enabled"] = False
        return RuntimeBindingResult(
            binding_id=uuid.uuid4().hex,
            execution_id=request.execution_id,
            decision="ALLOW",
            applied=False,
            reason="enforcement binding disabled",
            metadata=metadata,
        )


def _build_metadata(
    request: RuntimeBindingRequest,
    *,
    decision: RuntimeBindingDecision,
) -> dict[str, Any]:
    metadata = {
        "enforcement_id": request.enforcement_result.enforcement_id,
        "enforcement_status": request.enforcement_result.status,
        "binding_decision": decision,
        "observation_only": True,
    }
    if request.runtime_context:
        metadata["runtime_context"] = dict(request.runtime_context)
    if request.metadata:
        metadata.update(dict(request.metadata))
    if request.enforcement_result.metadata:
        metadata.update(
            {
                key: value
                for key, value in request.enforcement_result.metadata.items()
                if key not in metadata
            }
        )
    return metadata

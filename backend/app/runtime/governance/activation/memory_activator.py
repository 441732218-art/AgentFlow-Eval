# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory governance runtime activator."""

from __future__ import annotations

import threading
from typing import Any

from app.runtime.governance.activation.models import (
    GovernanceActivationRequest,
    GovernanceActivationResult,
)


class InMemoryGovernanceRuntimeActivator:
    """Thread-safe in-memory governance runtime activator."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._activations: dict[str, GovernanceActivationResult] = {}
        self._history: list[GovernanceActivationResult] = []
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable governance runtime activation."""
        with self._lock:
            self._enabled = enabled

    def activate(self, request: GovernanceActivationRequest) -> GovernanceActivationResult:
        """Return an activation decision without runtime execution."""
        with self._lock:
            if not self._enabled:
                result = _build_disabled_result(request)
            else:
                result = _build_enabled_result(request)
            self._activations[request.execution_id] = result
            self._history.append(result)
            return result

    def get_activation(self, execution_id: str) -> GovernanceActivationResult | None:
        """Return the latest activation result for an execution."""
        with self._lock:
            return self._activations.get(execution_id)

    def list_activations(
        self,
        *,
        execution_id: str | None = None,
    ) -> list[GovernanceActivationResult]:
        """Return recorded activation results."""
        with self._lock:
            records = list(self._history)
        if execution_id is not None:
            records = [
                record for record in records if record.execution_id == execution_id
            ]
        return records

    def clear(self) -> None:
        """Remove all recorded activation results."""
        with self._lock:
            self._activations.clear()
            self._history.clear()


def _build_enabled_result(
    request: GovernanceActivationRequest,
) -> GovernanceActivationResult:
    return GovernanceActivationResult(
        execution_id=request.execution_id,
        activated=True,
        governance_enabled=True,
        message="governance runtime activated",
        metadata=_build_metadata(request, source="governance_activation"),
    )


def _build_disabled_result(
    request: GovernanceActivationRequest,
) -> GovernanceActivationResult:
    return GovernanceActivationResult(
        execution_id=request.execution_id,
        activated=False,
        governance_enabled=False,
        message="governance runtime activation disabled",
        metadata=_build_metadata(request, source="governance_activation_disabled"),
    )


def _build_metadata(
    request: GovernanceActivationRequest,
    *,
    source: str,
) -> dict[str, Any]:
    metadata = {"source": source}
    if request.runtime_context:
        metadata["runtime_context"] = dict(request.runtime_context)
    if request.metadata:
        metadata.update(dict(request.metadata))
    return metadata

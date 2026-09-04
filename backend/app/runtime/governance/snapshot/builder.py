# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance evaluation snapshot builder."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from app.runtime.governance.snapshot.models import (
    GovernanceBindingSnapshot,
    GovernanceSnapshot,
)

if TYPE_CHECKING:
    from app.runtime.governance.binding.models import RuntimeBindingResult
    from app.runtime.governance.configuration.models import GovernanceConfiguration
    from app.runtime.governance.enforcement_pipeline.models import EnforcementResult
    from app.runtime.governance.models import GovernanceDecision
    from app.runtime.governance.policy_binding.models import PolicyBindingResult


@dataclass(frozen=True)
class GovernanceSnapshotBuildRequest:
    """Input artifacts used to build a governance evaluation snapshot."""

    execution_id: str
    policy_binding: PolicyBindingResult | None = None
    configuration: GovernanceConfiguration | None = None
    decision: GovernanceDecision | None = None
    enforcement: EnforcementResult | None = None
    runtime_binding: RuntimeBindingResult | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class GovernanceSnapshotBuilder(Protocol):
    """Builds immutable governance evaluation snapshots."""

    def build(self, request: GovernanceSnapshotBuildRequest) -> GovernanceSnapshot:
        """Aggregate governance artifacts into one snapshot."""


class DefaultGovernanceSnapshotBuilder:
    """Default governance snapshot builder implementation."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable snapshot building."""
        self._enabled = enabled

    def build(self, request: GovernanceSnapshotBuildRequest) -> GovernanceSnapshot:
        """Aggregate optional governance artifacts into one snapshot."""
        if not self._enabled:
            return GovernanceSnapshot(
                snapshot_id=uuid.uuid4().hex,
                execution_id=request.execution_id,
                metadata={
                    "observation_only": True,
                    "snapshot_enabled": False,
                    **dict(request.metadata),
                },
            )

        policy_versions = _collect_policy_versions(request)
        binding_results = _collect_binding_results(request)
        metadata = {
            "observation_only": True,
            **dict(request.metadata),
        }
        if request.configuration is not None:
            metadata["configuration_name"] = request.configuration.name
            metadata["configuration_environment"] = request.configuration.environment
        if request.decision is not None:
            metadata["decision_status"] = request.decision.status
        if request.enforcement is not None:
            metadata["enforcement_id"] = request.enforcement.enforcement_id

        return GovernanceSnapshot(
            snapshot_id=uuid.uuid4().hex,
            execution_id=request.execution_id,
            policy_versions=policy_versions,
            configuration_id=(
                request.configuration.configuration_id if request.configuration else None
            ),
            decision_id=request.decision.decision_id if request.decision else None,
            enforcement_status=(
                request.enforcement.status if request.enforcement else None
            ),
            binding_results=binding_results,
            metadata=metadata,
        )


def _collect_policy_versions(request: GovernanceSnapshotBuildRequest) -> tuple[str, ...]:
    if request.policy_binding is None:
        return ()
    return (
        f"{request.policy_binding.policy_id}@{request.policy_binding.policy_version}",
    )


def _collect_binding_results(
    request: GovernanceSnapshotBuildRequest,
) -> tuple[GovernanceBindingSnapshot, ...]:
    bindings: list[GovernanceBindingSnapshot] = []
    if request.policy_binding is not None:
        bindings.append(
            GovernanceBindingSnapshot(
                binding_id=request.policy_binding.binding_id,
                binding_type="policy",
                status=request.policy_binding.status,
                applied=request.policy_binding.applied,
                metadata={
                    "policy_id": request.policy_binding.policy_id,
                    "policy_version": request.policy_binding.policy_version,
                    **dict(request.policy_binding.metadata),
                },
            )
        )
    if request.runtime_binding is not None:
        bindings.append(
            GovernanceBindingSnapshot(
                binding_id=request.runtime_binding.binding_id,
                binding_type="runtime",
                status=request.runtime_binding.decision,
                applied=request.runtime_binding.applied,
                metadata={
                    "reason": request.runtime_binding.reason,
                    **dict(request.runtime_binding.metadata),
                },
            )
        )
    return tuple(bindings)

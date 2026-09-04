# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance evidence correlation builder."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from app.runtime.governance.evidence_correlation.models import (
    EvidenceCorrelation,
    GovernanceEvidenceReference,
)

if TYPE_CHECKING:
    from app.runtime.evidence.models import ExecutionEvidence
    from app.runtime.governance.models import GovernanceDecision
    from app.runtime.governance.snapshot.models import GovernanceSnapshot


@dataclass(frozen=True)
class EvidenceCorrelationBuildRequest:
    """Input artifacts used to build an evidence correlation record."""

    execution_id: str
    evidence: ExecutionEvidence | None = None
    decision: GovernanceDecision | None = None
    snapshot: GovernanceSnapshot | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class EvidenceCorrelationBuilder(Protocol):
    """Builds immutable governance evidence correlation records."""

    def build(self, request: EvidenceCorrelationBuildRequest) -> EvidenceCorrelation:
        """Correlate execution evidence with governance artifacts."""


class DefaultEvidenceCorrelationBuilder:
    """Default governance evidence correlation builder."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable evidence correlation building."""
        self._enabled = enabled

    def build(self, request: EvidenceCorrelationBuildRequest) -> EvidenceCorrelation:
        """Correlate optional evidence, decision, and snapshot artifacts."""
        if not self._enabled:
            return EvidenceCorrelation(
                correlation_id=uuid.uuid4().hex,
                execution_id=request.execution_id,
                metadata={
                    "observation_only": True,
                    "correlation_enabled": False,
                    **dict(request.metadata),
                },
            )

        references = _collect_references(request)
        metadata = {
            "observation_only": True,
            **dict(request.metadata),
        }
        if request.evidence is not None:
            metadata["evidence_status"] = request.evidence.status
            metadata["agent_id"] = request.evidence.agent_id
        if request.decision is not None:
            metadata["decision_status"] = request.decision.status
        if request.snapshot is not None:
            metadata["snapshot_enforcement_status"] = request.snapshot.enforcement_status

        return EvidenceCorrelation(
            correlation_id=uuid.uuid4().hex,
            execution_id=request.execution_id,
            evidence_id=request.evidence.evidence_id if request.evidence else None,
            decision_id=request.decision.decision_id if request.decision else None,
            snapshot_id=request.snapshot.snapshot_id if request.snapshot else None,
            references=references,
            metadata=metadata,
        )


def _collect_references(
    request: EvidenceCorrelationBuildRequest,
) -> tuple[GovernanceEvidenceReference, ...]:
    references: list[GovernanceEvidenceReference] = []
    if request.evidence is not None:
        references.append(
            GovernanceEvidenceReference(
                reference_id=uuid.uuid4().hex,
                reference_type="evidence",
                execution_id=request.execution_id,
                artifact_id=request.evidence.evidence_id,
                metadata={
                    "agent_id": request.evidence.agent_id,
                    "status": request.evidence.status,
                    "correlation_id": request.evidence.correlation_id,
                },
            )
        )
    if request.decision is not None:
        references.append(
            GovernanceEvidenceReference(
                reference_id=uuid.uuid4().hex,
                reference_type="decision",
                execution_id=request.execution_id,
                artifact_id=request.decision.decision_id,
                metadata={
                    "status": request.decision.status,
                    "agent_id": request.decision.agent_id,
                },
            )
        )
    if request.snapshot is not None:
        references.append(
            GovernanceEvidenceReference(
                reference_id=uuid.uuid4().hex,
                reference_type="snapshot",
                execution_id=request.execution_id,
                artifact_id=request.snapshot.snapshot_id,
                metadata={
                    "configuration_id": request.snapshot.configuration_id,
                    "decision_id": request.snapshot.decision_id,
                    "enforcement_status": request.snapshot.enforcement_status,
                },
            )
        )
    return tuple(references)

# AgentFlow Intelligence v2.0 — Governance evidence correlation tests (Phase 12.10)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.governance.evidence_correlation.builder import (
    DefaultEvidenceCorrelationBuilder,
    EvidenceCorrelationBuildRequest,
)
from app.runtime.governance.evidence_correlation.memory_store import (
    InMemoryEvidenceCorrelationStore,
)
from app.runtime.governance.evidence_correlation.models import (
    EvidenceCorrelation,
    GovernanceEvidenceReference,
)
from app.runtime.governance.models import GovernanceDecision
from app.runtime.governance.snapshot.models import GovernanceSnapshot

_CORRELATION_ROOT = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "runtime"
    / "governance"
    / "evidence_correlation"
)
_FORBIDDEN_STRINGS = (
    "app.applications",
    "app.api",
    "app.service",
    "app.tracing",
    "app.runtime.memory",
    "app.core",
    "openai",
    "langgraph",
    "sqlalchemy",
    "postgres",
    "trade_provider",
    "kafka",
    "redis",
    "PolicyEngine",
    "PermissionEvaluator",
    "ToolExecutionEngine",
    "AgentRuntime",
    "AgentExecutionPipeline",
    "ExecutionContext",
)


def _evidence() -> ExecutionEvidence:
    return ExecutionEvidence(
        evidence_id="evidence-correlation-1",
        execution_id="exec-correlation-1",
        agent_id="agent-correlation-1",
        correlation_id="corr-1",
        status="COMPLETED",
    )


def _decision() -> GovernanceDecision:
    return GovernanceDecision(
        decision_id="decision-correlation-1",
        execution_id="exec-correlation-1",
        agent_id="agent-correlation-1",
        status="WARN",
        evaluated_at=datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc),
    )


def _snapshot() -> GovernanceSnapshot:
    return GovernanceSnapshot(
        snapshot_id="snapshot-correlation-1",
        execution_id="exec-correlation-1",
        decision_id="decision-correlation-1",
        enforcement_status="WARN",
    )


def _build_request(**overrides: object) -> EvidenceCorrelationBuildRequest:
    values = {
        "execution_id": "exec-correlation-1",
        "evidence": _evidence(),
        "decision": _decision(),
        "snapshot": _snapshot(),
        "metadata": {"source": "test"},
    }
    values.update(overrides)
    return EvidenceCorrelationBuildRequest(**values)  # type: ignore[arg-type]


def test_evidence_correlation_model_creation() -> None:
    correlation = EvidenceCorrelation(
        correlation_id="correlation-1",
        execution_id="exec-correlation-1",
        evidence_id="evidence-correlation-1",
        decision_id="decision-correlation-1",
        snapshot_id="snapshot-correlation-1",
    )

    assert correlation.correlation_id == "correlation-1"
    assert correlation.evidence_id == "evidence-correlation-1"
    assert correlation.snapshot_id == "snapshot-correlation-1"


def test_governance_evidence_reference_is_immutable() -> None:
    reference = GovernanceEvidenceReference(
        reference_id="reference-1",
        reference_type="evidence",
        execution_id="exec-correlation-1",
        artifact_id="evidence-correlation-1",
    )

    with pytest.raises(FrozenInstanceError):
        reference.artifact_id = "other-evidence"  # type: ignore[misc]

    updated = reference.with_updates(artifact_id="other-evidence")
    assert updated.artifact_id == "other-evidence"
    assert reference.artifact_id == "evidence-correlation-1"


def test_evidence_correlation_is_immutable() -> None:
    correlation = EvidenceCorrelation(
        correlation_id="correlation-1",
        execution_id="exec-correlation-1",
    )

    with pytest.raises(FrozenInstanceError):
        correlation.execution_id = "other-exec"  # type: ignore[misc]

    updated = correlation.with_updates(execution_id="other-exec")
    assert updated.execution_id == "other-exec"
    assert correlation.execution_id == "exec-correlation-1"


def test_builder_links_execution_evidence() -> None:
    builder = DefaultEvidenceCorrelationBuilder()
    correlation = builder.build(_build_request())

    assert correlation.evidence_id == "evidence-correlation-1"
    evidence_refs = [
        reference for reference in correlation.references if reference.reference_type == "evidence"
    ]
    assert len(evidence_refs) == 1
    assert evidence_refs[0].artifact_id == "evidence-correlation-1"
    assert correlation.metadata["evidence_status"] == "COMPLETED"


def test_builder_links_governance_decision() -> None:
    builder = DefaultEvidenceCorrelationBuilder()
    correlation = builder.build(_build_request())

    assert correlation.decision_id == "decision-correlation-1"
    decision_refs = [
        reference for reference in correlation.references if reference.reference_type == "decision"
    ]
    assert len(decision_refs) == 1
    assert decision_refs[0].metadata["status"] == "WARN"


def test_builder_links_governance_snapshot() -> None:
    builder = DefaultEvidenceCorrelationBuilder()
    correlation = builder.build(_build_request())

    assert correlation.snapshot_id == "snapshot-correlation-1"
    snapshot_refs = [
        reference for reference in correlation.references if reference.reference_type == "snapshot"
    ]
    assert len(snapshot_refs) == 1
    assert snapshot_refs[0].metadata["enforcement_status"] == "WARN"


def test_store_save_get_remove_and_clear() -> None:
    store = InMemoryEvidenceCorrelationStore()
    builder = DefaultEvidenceCorrelationBuilder()
    correlation = builder.build(_build_request())

    store.save(correlation)
    retrieved = store.get(correlation.correlation_id)

    assert retrieved == correlation

    store.remove(correlation.correlation_id)
    assert store.get(correlation.correlation_id) is None

    store.save(correlation)
    store.clear()
    assert store.get(correlation.correlation_id) is None


def test_store_list_by_execution_and_list_all() -> None:
    store = InMemoryEvidenceCorrelationStore()
    builder = DefaultEvidenceCorrelationBuilder()
    first = builder.build(_build_request(execution_id="exec-a"))
    second = builder.build(_build_request(execution_id="exec-b"))

    store.save(first)
    store.save(second)

    assert len(store.list_all()) == 2
    assert len(store.list_by_execution("exec-a")) == 1
    assert store.list_by_execution("exec-a")[0].execution_id == "exec-a"


def test_builder_disabled_behavior() -> None:
    builder = DefaultEvidenceCorrelationBuilder(enabled=False)
    correlation = builder.build(_build_request())

    assert correlation.evidence_id is None
    assert correlation.decision_id is None
    assert correlation.snapshot_id is None
    assert correlation.references == ()
    assert correlation.metadata["correlation_enabled"] is False


def test_builder_with_partial_artifacts() -> None:
    builder = DefaultEvidenceCorrelationBuilder()
    correlation = builder.build(
        EvidenceCorrelationBuildRequest(
            execution_id="exec-correlation-2",
            evidence=_evidence(),
        )
    )

    assert correlation.evidence_id == "evidence-correlation-1"
    assert correlation.decision_id is None
    assert correlation.snapshot_id is None
    assert len(correlation.references) == 1


def test_store_is_thread_safe() -> None:
    store = InMemoryEvidenceCorrelationStore()
    builder = DefaultEvidenceCorrelationBuilder()
    errors: list[Exception] = []

    def worker(index: int) -> None:
        try:
            correlation = builder.build(
                EvidenceCorrelationBuildRequest(
                    execution_id=f"exec-thread-{index}",
                    evidence=_evidence(),
                )
            )
            store.save(correlation)
            store.get(correlation.correlation_id)
        except Exception as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(24)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(store.list_all()) == 24


def test_governance_evidence_correlation_has_no_forbidden_dependencies() -> None:
    for path in _CORRELATION_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

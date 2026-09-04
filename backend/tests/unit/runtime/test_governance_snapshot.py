# AgentFlow Intelligence v2.0 — Governance snapshot tests (Phase 12.11)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.runtime.governance.binding.models import RuntimeBindingResult
from app.runtime.governance.configuration.models import GovernanceConfiguration
from app.runtime.governance.enforcement_pipeline.models import EnforcementResult
from app.runtime.governance.models import GovernanceDecision
from app.runtime.governance.policy_binding.models import PolicyBindingResult
from app.runtime.governance.snapshot.builder import (
    DefaultGovernanceSnapshotBuilder,
    GovernanceSnapshotBuildRequest,
)
from app.runtime.governance.snapshot.memory_store import InMemoryGovernanceSnapshotStore
from app.runtime.governance.snapshot.models import GovernanceBindingSnapshot, GovernanceSnapshot

_SNAPSHOT_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "snapshot"
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


def _policy_binding() -> PolicyBindingResult:
    return PolicyBindingResult(
        binding_id="policy-binding-1",
        policy_id="policy-1",
        policy_version="1.0.0",
        execution_id="exec-snapshot-1",
        status="BOUND",
        applied=True,
        metadata={"source": "test"},
    )


def _configuration() -> GovernanceConfiguration:
    return GovernanceConfiguration(
        configuration_id="config-1",
        name="Snapshot Config",
        description="Snapshot configuration",
        enabled=True,
        environment="production",
    )


def _decision() -> GovernanceDecision:
    return GovernanceDecision(
        decision_id="decision-snapshot-1",
        execution_id="exec-snapshot-1",
        agent_id="agent-snapshot-1",
        status="WARN",
        reasons=("risk detected",),
        evaluated_at=datetime(2026, 9, 4, 9, 0, tzinfo=timezone.utc),
    )


def _enforcement() -> EnforcementResult:
    return EnforcementResult(
        enforcement_id="enforcement-snapshot-1",
        execution_id="exec-snapshot-1",
        status="WARN",
        reason="enforcement warn",
        timestamp=datetime(2026, 9, 4, 9, 0, tzinfo=timezone.utc),
    )


def _runtime_binding() -> RuntimeBindingResult:
    return RuntimeBindingResult(
        binding_id="runtime-binding-1",
        execution_id="exec-snapshot-1",
        decision="WARN",
        applied=True,
        reason="runtime binding warn",
        timestamp=datetime(2026, 9, 4, 9, 0, tzinfo=timezone.utc),
    )


def _build_request(**overrides: object) -> GovernanceSnapshotBuildRequest:
    values = {
        "execution_id": "exec-snapshot-1",
        "policy_binding": _policy_binding(),
        "configuration": _configuration(),
        "decision": _decision(),
        "enforcement": _enforcement(),
        "runtime_binding": _runtime_binding(),
        "metadata": {"correlation_id": "corr-1"},
    }
    values.update(overrides)
    return GovernanceSnapshotBuildRequest(**values)  # type: ignore[arg-type]


def test_governance_snapshot_model_creation() -> None:
    snapshot = GovernanceSnapshot(
        snapshot_id="snapshot-1",
        execution_id="exec-snapshot-1",
        policy_versions=("policy-1@1.0.0",),
        configuration_id="config-1",
        decision_id="decision-snapshot-1",
        enforcement_status="WARN",
    )

    assert snapshot.snapshot_id == "snapshot-1"
    assert snapshot.execution_id == "exec-snapshot-1"
    assert snapshot.policy_versions == ("policy-1@1.0.0",)


def test_governance_snapshot_is_immutable() -> None:
    snapshot = GovernanceSnapshot(
        snapshot_id="snapshot-1",
        execution_id="exec-snapshot-1",
    )

    with pytest.raises(FrozenInstanceError):
        snapshot.execution_id = "other-exec"  # type: ignore[misc]

    updated = snapshot.with_updates(execution_id="other-exec")
    assert updated.execution_id == "other-exec"
    assert snapshot.execution_id == "exec-snapshot-1"


def test_builder_aggregates_all_governance_artifacts() -> None:
    builder = DefaultGovernanceSnapshotBuilder()
    snapshot = builder.build(_build_request())

    assert snapshot.execution_id == "exec-snapshot-1"
    assert snapshot.policy_versions == ("policy-1@1.0.0",)
    assert snapshot.configuration_id == "config-1"
    assert snapshot.decision_id == "decision-snapshot-1"
    assert snapshot.enforcement_status == "WARN"
    assert len(snapshot.binding_results) == 2
    assert snapshot.metadata["observation_only"] is True


def test_builder_captures_policy_snapshot() -> None:
    builder = DefaultGovernanceSnapshotBuilder()
    snapshot = builder.build(_build_request())

    policy_binding = snapshot.binding_results[0]
    assert policy_binding.binding_type == "policy"
    assert policy_binding.status == "BOUND"
    assert policy_binding.metadata["policy_id"] == "policy-1"


def test_builder_captures_configuration_snapshot() -> None:
    builder = DefaultGovernanceSnapshotBuilder()
    snapshot = builder.build(_build_request())

    assert snapshot.configuration_id == "config-1"
    assert snapshot.metadata["configuration_name"] == "Snapshot Config"
    assert snapshot.metadata["configuration_environment"] == "production"


def test_builder_captures_decision_snapshot() -> None:
    builder = DefaultGovernanceSnapshotBuilder()
    snapshot = builder.build(_build_request())

    assert snapshot.decision_id == "decision-snapshot-1"
    assert snapshot.metadata["decision_status"] == "WARN"


def test_builder_captures_enforcement_snapshot() -> None:
    builder = DefaultGovernanceSnapshotBuilder()
    snapshot = builder.build(_build_request())

    assert snapshot.enforcement_status == "WARN"
    assert snapshot.metadata["enforcement_id"] == "enforcement-snapshot-1"


def test_builder_captures_runtime_binding_snapshot() -> None:
    builder = DefaultGovernanceSnapshotBuilder()
    snapshot = builder.build(_build_request())

    runtime_binding = snapshot.binding_results[1]
    assert runtime_binding.binding_type == "runtime"
    assert runtime_binding.status == "WARN"
    assert runtime_binding.metadata["reason"] == "runtime binding warn"


def test_store_save_get_list_and_clear() -> None:
    store = InMemoryGovernanceSnapshotStore()
    builder = DefaultGovernanceSnapshotBuilder()
    first = builder.build(_build_request())
    second = builder.build(_build_request(metadata={"phase": "second"}))

    store.save(first)
    store.save(second)

    retrieved = store.get(first.snapshot_id)
    listed = store.list_by_execution("exec-snapshot-1")

    assert retrieved == first
    assert len(listed) == 2

    store.clear()

    assert store.get(first.snapshot_id) is None
    assert store.list_by_execution("exec-snapshot-1") == []


def test_store_get_returns_none_for_missing_snapshot() -> None:
    store = InMemoryGovernanceSnapshotStore()

    assert store.get("missing-snapshot") is None


def test_binding_snapshot_is_immutable() -> None:
    binding = GovernanceBindingSnapshot(
        binding_id="binding-1",
        binding_type="policy",
        status="BOUND",
        applied=True,
    )

    with pytest.raises(FrozenInstanceError):
        binding.applied = False  # type: ignore[misc]

    updated = binding.with_updates(applied=False)
    assert updated.applied is False
    assert binding.applied is True


def test_builder_disabled_behavior() -> None:
    builder = DefaultGovernanceSnapshotBuilder(enabled=False)
    snapshot = builder.build(_build_request())

    assert snapshot.policy_versions == ()
    assert snapshot.configuration_id is None
    assert snapshot.decision_id is None
    assert snapshot.enforcement_status is None
    assert snapshot.binding_results == ()
    assert snapshot.metadata["snapshot_enabled"] is False


def test_builder_with_partial_artifacts() -> None:
    builder = DefaultGovernanceSnapshotBuilder()
    snapshot = builder.build(
        GovernanceSnapshotBuildRequest(
            execution_id="exec-snapshot-2",
            decision=_decision(),
        )
    )

    assert snapshot.decision_id == "decision-snapshot-1"
    assert snapshot.policy_versions == ()
    assert snapshot.binding_results == ()


def test_store_is_thread_safe() -> None:
    store = InMemoryGovernanceSnapshotStore()
    builder = DefaultGovernanceSnapshotBuilder()
    errors: list[Exception] = []

    def worker(index: int) -> None:
        try:
            snapshot = builder.build(
                GovernanceSnapshotBuildRequest(
                    execution_id=f"exec-thread-{index}",
                    decision=_decision(),
                )
            )
            store.save(snapshot)
            store.get(snapshot.snapshot_id)
        except Exception as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(24)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(store.list_by_execution("exec-thread-0")) >= 1


def test_governance_snapshot_has_no_forbidden_dependencies() -> None:
    for path in _SNAPSHOT_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

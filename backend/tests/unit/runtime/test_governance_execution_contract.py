# AgentFlow Intelligence v2.0 — Governance execution contract tests (Phase 13.1)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.runtime.governance.execution.memory_executor import InMemoryGovernanceExecutionContract
from app.runtime.governance.execution.models import (
    GovernanceExecutionEffect,
    GovernanceExecutionRecord,
)

_EXECUTION_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "execution"
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


def _effect(
    *,
    action_type: str = "ALLOW",
    effect_id: str = "effect-1",
) -> GovernanceExecutionEffect:
    return GovernanceExecutionEffect(
        effect_id=effect_id,
        decision_id="decision-1",
        action_type=action_type,  # type: ignore[arg-type]
        target="execution:exec-1",
        reason="governance execution effect",
        evidence_reference="evidence-1",
        metadata={"source": "test"},
    )


def test_governance_execution_effect_model_creation() -> None:
    effect = _effect(action_type="WARN")

    assert effect.effect_id == "effect-1"
    assert effect.action_type == "WARN"
    assert effect.evidence_reference == "evidence-1"


def test_governance_execution_effect_is_immutable() -> None:
    effect = _effect()

    with pytest.raises(FrozenInstanceError):
        effect.target = "other-target"  # type: ignore[misc]

    updated = effect.with_updates(target="other-target")
    assert updated.target == "other-target"
    assert effect.target == "execution:exec-1"


def test_governance_execution_record_is_immutable() -> None:
    record = GovernanceExecutionRecord(
        effect_id="effect-1",
        decision_id="decision-1",
        action_type="ALLOW",
        target="execution:exec-1",
        reason="record",
        evidence_reference="evidence-1",
        applied=True,
    )

    with pytest.raises(FrozenInstanceError):
        record.applied = False  # type: ignore[misc]

    updated = record.with_updates(applied=False)
    assert updated.applied is False
    assert record.applied is True


def test_execute_records_governance_execution() -> None:
    contract = InMemoryGovernanceExecutionContract()
    record = contract.execute(_effect(action_type="BLOCK"))

    assert record.action_type == "BLOCK"
    assert record.applied is True
    assert record.metadata["observation_only"] is True


def test_get_execution_returns_record() -> None:
    contract = InMemoryGovernanceExecutionContract()
    record = contract.execute(_effect())

    retrieved = contract.get_execution("effect-1")

    assert retrieved == record


def test_list_executions_returns_sorted_records() -> None:
    contract = InMemoryGovernanceExecutionContract()
    contract.execute(_effect(effect_id="effect-a"))
    contract.execute(_effect(effect_id="effect-b", action_type="WARN"))

    records = contract.list_executions()

    assert len(records) == 2
    assert {record.effect_id for record in records} == {"effect-a", "effect-b"}


def test_clear_removes_execution_history() -> None:
    contract = InMemoryGovernanceExecutionContract()
    contract.execute(_effect())

    contract.clear()

    assert contract.list_executions() == []
    assert contract.get_execution("effect-1") is None


def test_disabled_mode_does_not_apply_execution() -> None:
    contract = InMemoryGovernanceExecutionContract(enabled=False)
    record = contract.execute(_effect(action_type="BLOCK"))

    assert record.action_type == "ALLOW"
    assert record.applied is False
    assert record.reason == "governance execution contract disabled"
    assert record.metadata["execution_enabled"] is False


def test_unsupported_action_type_raises() -> None:
    contract = InMemoryGovernanceExecutionContract()
    effect = _effect(action_type="ALLOW").with_updates(action_type="UNKNOWN")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Unsupported governance execution action type"):
        contract.execute(effect)


def test_contract_is_thread_safe() -> None:
    contract = InMemoryGovernanceExecutionContract()
    errors: list[Exception] = []
    action_types = ("ALLOW", "WARN", "BLOCK", "REQUIRE_APPROVAL")

    def worker(index: int) -> None:
        try:
            contract.execute(
                _effect(
                    effect_id=f"effect-thread-{index}",
                    action_type=action_types[index % len(action_types)],
                )
            )
        except Exception as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(24)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(contract.list_executions()) == 24


def test_governance_execution_contract_has_no_forbidden_dependencies() -> None:
    for path in _EXECUTION_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

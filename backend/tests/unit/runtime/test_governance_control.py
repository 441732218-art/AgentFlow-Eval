# AgentFlow Intelligence v2.0 — Runtime governance control tests (Phase 12.4)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.runtime.governance.control.memory_controller import InMemoryGovernanceController
from app.runtime.governance.control.models import GovernanceControlDecision
from app.runtime.governance.models import GovernanceDecision

_CONTROL_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "control"
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
    "GovernanceLifecycleManager",
    "AgentRuntime",
    "AgentExecutionPipeline",
    "ExecutionContext",
)


def _decision(
    *,
    status: str,
    reasons: tuple[str, ...] = (),
    execution_id: str = "exec-control-1",
    metadata: dict[str, object] | None = None,
) -> GovernanceDecision:
    return GovernanceDecision(
        decision_id="decision-control-1",
        execution_id=execution_id,
        agent_id="agent-control-1",
        status=status,  # type: ignore[arg-type]
        reasons=reasons,
        evaluated_at=datetime(2026, 9, 4, 3, 0, tzinfo=timezone.utc),
        metadata=dict(metadata or {"source": "test"}),
    )


def test_governance_control_decision_is_immutable() -> None:
    control = GovernanceControlDecision(
        control_id="control-1",
        execution_id="exec-control-1",
        decision_status="ALLOW",
        action_type="ALLOW",
        reason="all clear",
    )

    with pytest.raises(FrozenInstanceError):
        control.action_type = "BLOCK"  # type: ignore[misc]

    updated = control.with_updates(action_type="BLOCK", decision_status="BLOCK")
    assert updated.action_type == "BLOCK"
    assert updated.decision_status == "BLOCK"
    assert control.action_type == "ALLOW"


def test_allow_decision_maps_to_allow_control() -> None:
    controller = InMemoryGovernanceController()
    control = controller.evaluate(_decision(status="ALLOW"))

    assert control.decision_status == "ALLOW"
    assert control.action_type == "ALLOW"
    assert control.execution_id == "exec-control-1"


def test_warn_decision_maps_to_warn_control() -> None:
    controller = InMemoryGovernanceController()
    control = controller.evaluate(_decision(status="WARN", reasons=("risk detected",)))

    assert control.decision_status == "WARN"
    assert control.action_type == "WARN"
    assert control.reason == "risk detected"


def test_deny_decision_maps_to_block_control() -> None:
    controller = InMemoryGovernanceController()
    control = controller.evaluate(_decision(status="DENY", reasons=("policy violation",)))

    assert control.decision_status == "BLOCK"
    assert control.action_type == "BLOCK"
    assert control.reason == "policy violation"


def test_evaluate_records_control_decisions() -> None:
    controller = InMemoryGovernanceController()
    controller.evaluate(_decision(status="ALLOW"))
    controller.evaluate(_decision(status="DENY", execution_id="exec-control-2"))

    records = controller.list_decisions()
    assert len(records) == 2
    assert {record.execution_id for record in records} == {
        "exec-control-1",
        "exec-control-2",
    }


def test_list_decisions_filters_by_execution_id() -> None:
    controller = InMemoryGovernanceController()
    controller.evaluate(_decision(status="ALLOW", execution_id="exec-a"))
    controller.evaluate(_decision(status="WARN", execution_id="exec-b"))

    filtered = controller.list_decisions(execution_id="exec-a")
    assert len(filtered) == 1
    assert filtered[0].execution_id == "exec-a"


def test_clear_removes_recorded_decisions() -> None:
    controller = InMemoryGovernanceController()
    controller.evaluate(_decision(status="ALLOW"))

    controller.clear()

    assert controller.list_decisions() == []


def test_disabled_controller_returns_allow_without_blocking() -> None:
    controller = InMemoryGovernanceController(enabled=False)
    control = controller.evaluate(_decision(status="DENY", reasons=("should not block",)))

    assert control.decision_status == "ALLOW"
    assert control.action_type == "ALLOW"
    assert control.metadata["control_enabled"] is False
    assert control.reason == "control evaluation disabled"


def test_metadata_propagates_from_governance_decision() -> None:
    controller = InMemoryGovernanceController()
    control = controller.evaluate(
        _decision(
            status="WARN",
            metadata={"rule_id": "rule-42", "severity": "medium"},
        )
    )

    assert control.metadata["decision_id"] == "decision-control-1"
    assert control.metadata["agent_id"] == "agent-control-1"
    assert control.metadata["source_decision_status"] == "WARN"
    assert control.metadata["rule_id"] == "rule-42"
    assert control.metadata["severity"] == "medium"


def test_controller_is_thread_safe() -> None:
    controller = InMemoryGovernanceController()
    errors: list[Exception] = []

    def worker(index: int) -> None:
        try:
            controller.evaluate(
                _decision(
                    status="ALLOW" if index % 2 == 0 else "DENY",
                    execution_id=f"exec-thread-{index}",
                )
            )
        except Exception as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(controller.list_decisions()) == 20


def test_unsupported_decision_status_raises() -> None:
    controller = InMemoryGovernanceController()
    invalid = replace(_decision(status="ALLOW"), status="UNKNOWN")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Unsupported governance decision status"):
        controller.evaluate(invalid)


def test_governance_control_layer_has_no_forbidden_dependencies() -> None:
    for path in _CONTROL_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

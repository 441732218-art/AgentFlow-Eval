# AgentFlow Intelligence v2.0 — Runtime governance enforcement tests (Phase 11.7)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.runtime.governance.enforcement.memory_enforcer import InMemoryGovernanceEnforcer
from app.runtime.governance.enforcement.models import GovernanceAction
from app.runtime.governance.models import GovernanceDecision

_ENFORCEMENT_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "enforcement"
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
    "AuditRecorder",
    "EventPublisher",
    "EvidenceCollector",
    "EvidenceQueryService",
    "ToolExecutionEngine",
    "GovernanceLifecycle",
    "AgentRuntime",
    "AgentExecutionPipeline",
)


def _decision(
    *,
    status: str,
    reasons: tuple[str, ...] = (),
    execution_id: str = "exec-enforce-1",
    metadata: dict[str, object] | None = None,
) -> GovernanceDecision:
    return GovernanceDecision(
        decision_id="decision-enforce-1",
        execution_id=execution_id,
        agent_id="agent-enforce-1",
        status=status,  # type: ignore[arg-type]
        reasons=reasons,
        evaluated_at=datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc),
        metadata=dict(metadata or {"source": "test"}),
    )


def test_governance_action_is_immutable() -> None:
    action = GovernanceAction(
        action_id="action-1",
        execution_id="exec-enforce-1",
        decision_status="ALLOW",
        action_type="ALLOW",
        reason="all clear",
    )

    with pytest.raises(FrozenInstanceError):
        action.action_type = "BLOCK"  # type: ignore[misc]

    updated = action.with_updates(action_type="BLOCK")
    assert updated.action_type == "BLOCK"
    assert action.action_type == "ALLOW"


def test_allow_enforcement() -> None:
    enforcer = InMemoryGovernanceEnforcer()
    decision = _decision(status="ALLOW", reasons=("policy satisfied",))

    action = enforcer.enforce(decision)

    assert action.action_type == "ALLOW"
    assert action.decision_status == "ALLOW"
    assert action.reason == "policy satisfied"


def test_warn_enforcement() -> None:
    enforcer = InMemoryGovernanceEnforcer()
    decision = _decision(status="WARN", reasons=("execution anomaly",))

    action = enforcer.enforce(decision)

    assert action.action_type == "WARN"
    assert action.decision_status == "WARN"
    assert action.reason == "execution anomaly"


def test_deny_enforcement() -> None:
    enforcer = InMemoryGovernanceEnforcer()
    decision = _decision(status="DENY", reasons=("permission denied",))

    action = enforcer.enforce(decision)

    assert action.action_type == "BLOCK"
    assert action.decision_status == "DENY"
    assert action.reason == "permission denied"


def test_invalid_decision_handling() -> None:
    enforcer = InMemoryGovernanceEnforcer()
    invalid = replace(_decision(status="ALLOW"), status="UNKNOWN")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Unsupported governance decision status"):
        enforcer.enforce(invalid)


def test_enforcer_thread_safety() -> None:
    enforcer = InMemoryGovernanceEnforcer()
    errors: list[Exception] = []

    def enforce_many(prefix: str) -> None:
        try:
            for index in range(20):
                enforcer.enforce(
                    _decision(
                        status="ALLOW",
                        execution_id=f"exec-{prefix}-{index}",
                    )
                )
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=enforce_many, args=(f"t{i}",)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(enforcer.list_actions()) == 80


def test_action_metadata() -> None:
    enforcer = InMemoryGovernanceEnforcer()
    decision = _decision(
        status="WARN",
        reasons=("review required",),
        metadata={"rule_count": 2, "severity": "medium"},
    )

    action = enforcer.enforce(decision)

    assert action.execution_id == "exec-enforce-1"
    assert action.metadata["decision_id"] == "decision-enforce-1"
    assert action.metadata["agent_id"] == "agent-enforce-1"
    assert action.metadata["rule_count"] == 2
    assert action.metadata["severity"] == "medium"
    assert action.timestamp is not None


def test_multiple_decisions() -> None:
    enforcer = InMemoryGovernanceEnforcer()
    decisions = [
        _decision(status="ALLOW", execution_id="exec-1"),
        _decision(status="WARN", execution_id="exec-2", reasons=("warn",)),
        _decision(status="DENY", execution_id="exec-3", reasons=("deny",)),
    ]

    actions = [enforcer.enforce(decision) for decision in decisions]

    assert [action.action_type for action in actions] == ["ALLOW", "WARN", "BLOCK"]
    assert enforcer.list_actions(execution_id="exec-2") == [actions[1]]


def test_disabled_behavior() -> None:
    enforcer = InMemoryGovernanceEnforcer(enabled=False)
    decision = _decision(status="DENY", reasons=("should not block",))

    action = enforcer.enforce(decision)

    assert action.action_type == "ALLOW"
    assert action.reason == "enforcement disabled"
    assert action.metadata["enforcement_enabled"] is False
    assert action.decision_status == "DENY"


def test_enforcement_module_has_no_forbidden_dependencies() -> None:
    for path in _ENFORCEMENT_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

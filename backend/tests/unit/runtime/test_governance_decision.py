# AgentFlow Intelligence v2.0 — Runtime governance decision tests (Phase 11.6)

from __future__ import annotations

import uuid
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.runtime.evidence.models import ExecutionEvidence, PermissionDecision
from app.runtime.governance.evaluator import GovernanceEvaluator
from app.runtime.governance.memory_engine import InMemoryGovernanceEngine
from app.runtime.governance.models import GovernanceDecision, GovernanceRule
from app.runtime.governance.rules import GovernanceRule as GovernanceRuleProtocol

_GOVERNANCE_DECISION_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance"
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
)


def _evidence(**overrides: object) -> ExecutionEvidence:
    defaults = {
        "evidence_id": "evidence-gov-1",
        "execution_id": "exec-gov-1",
        "agent_id": "agent-gov-1",
        "correlation_id": "corr-gov-1",
        "status": "COMPLETED",
    }
    defaults.update(overrides)
    return ExecutionEvidence(**defaults)  # type: ignore[arg-type]


def _decision(
    *,
    status: str,
    reasons: tuple[str, ...] = (),
    execution_id: str = "exec-gov-1",
    agent_id: str = "agent-gov-1",
) -> GovernanceDecision:
    return GovernanceDecision(
        decision_id=uuid.uuid4().hex,
        execution_id=execution_id,
        agent_id=agent_id,
        status=status,  # type: ignore[arg-type]
        reasons=reasons,
    )


class _StaticRule:
    """Test rule returning a fixed governance decision."""

    def __init__(self, status: str, *, reasons: tuple[str, ...] = ()) -> None:
        self._status = status
        self._reasons = reasons

    def evaluate(self, evidence: ExecutionEvidence) -> GovernanceDecision:
        return _decision(
            status=self._status,
            reasons=self._reasons,
            execution_id=evidence.execution_id,
            agent_id=evidence.agent_id,
        )


class _PermissionDenyRule:
    """Rule that denies when permission decisions include DENY."""

    def evaluate(self, evidence: ExecutionEvidence) -> GovernanceDecision:
        denied = [
            decision
            for decision in evidence.permission_decisions
            if decision.decision == "DENY"
        ]
        if denied:
            return _decision(
                status="DENY",
                reasons=(f"permission denied for {denied[0].tool_name}",),
                execution_id=evidence.execution_id,
                agent_id=evidence.agent_id,
            )
        return _decision(
            status="ALLOW",
            execution_id=evidence.execution_id,
            agent_id=evidence.agent_id,
        )


class _FailedExecutionRule:
    """Rule that warns when execution evidence status is FAILED."""

    def evaluate(self, evidence: ExecutionEvidence) -> GovernanceDecision:
        if evidence.status == "FAILED":
            return _decision(
                status="WARN",
                reasons=("execution failed",),
                execution_id=evidence.execution_id,
                agent_id=evidence.agent_id,
            )
        return _decision(
            status="ALLOW",
            execution_id=evidence.execution_id,
            agent_id=evidence.agent_id,
        )


def test_governance_decision_is_immutable() -> None:
    decision = _decision(status="ALLOW", reasons=("ok",))

    with pytest.raises(FrozenInstanceError):
        decision.status = "DENY"  # type: ignore[misc]

    updated = decision.with_updates(status="DENY")
    assert updated.status == "DENY"
    assert decision.status == "ALLOW"


def test_rule_registration() -> None:
    engine = InMemoryGovernanceEngine()
    spec = GovernanceRule(
        rule_id="rule-allow",
        name="Allow Rule",
        description="Always allow",
    )

    engine.register_rule(spec, _StaticRule("ALLOW"))

    rules = engine.list_rules()
    assert len(rules) == 1
    assert rules[0].rule_id == "rule-allow"


def test_rule_removal() -> None:
    engine = InMemoryGovernanceEngine()
    spec = GovernanceRule(
        rule_id="rule-remove",
        name="Remove Rule",
        description="Temporary rule",
    )
    engine.register_rule(spec, _StaticRule("ALLOW"))

    engine.remove_rule("rule-remove")

    assert engine.list_rules() == []


def test_list_rules() -> None:
    engine = InMemoryGovernanceEngine()
    engine.register_rule(
        GovernanceRule(rule_id="rule-b", name="B", description="second"),
        _StaticRule("ALLOW"),
    )
    engine.register_rule(
        GovernanceRule(rule_id="rule-a", name="A", description="first"),
        _StaticRule("ALLOW"),
    )

    rules = engine.list_rules()

    assert [rule.rule_id for rule in rules] == ["rule-a", "rule-b"]


def test_allow_evaluation() -> None:
    engine = InMemoryGovernanceEngine()
    engine.register_rule(
        GovernanceRule(rule_id="rule-allow", name="Allow", description="allow"),
        _StaticRule("ALLOW", reasons=("all clear",)),
    )

    decision = engine.evaluate(_evidence())

    assert decision.status == "ALLOW"
    assert decision.reasons == ("all clear",)


def test_warn_evaluation() -> None:
    engine = InMemoryGovernanceEngine()
    engine.register_rule(
        GovernanceRule(rule_id="rule-warn", name="Warn", description="warn"),
        _FailedExecutionRule(),
    )

    decision = engine.evaluate(_evidence(status="FAILED"))

    assert decision.status == "WARN"
    assert decision.reasons == ("execution failed",)


def test_deny_evaluation() -> None:
    engine = InMemoryGovernanceEngine()
    engine.register_rule(
        GovernanceRule(rule_id="rule-deny", name="Deny", description="deny"),
        _PermissionDenyRule(),
    )
    evidence = _evidence(
        permission_decisions=(
            PermissionDecision(
                execution_id="exec-gov-1",
                decision="DENY",
                tool_name="email.send",
                permission="email.send",
            ),
        )
    )

    decision = engine.evaluate(evidence)

    assert decision.status == "DENY"
    assert "permission denied for email.send" in decision.reasons


def test_aggregation_priority() -> None:
    evaluator = GovernanceEvaluator()
    evidence = _evidence()

    deny_over_warn = evaluator.aggregate(
        evidence,
        [
            _decision(status="WARN", reasons=("warn",)),
            _decision(status="DENY", reasons=("deny",)),
            _decision(status="ALLOW"),
        ],
    )
    warn_over_allow = evaluator.aggregate(
        evidence,
        [
            _decision(status="ALLOW"),
            _decision(status="WARN", reasons=("warn",)),
        ],
    )

    assert deny_over_warn.status == "DENY"
    assert deny_over_warn.reasons == ("warn", "deny")
    assert warn_over_allow.status == "WARN"


def test_disabled_rule_ignored() -> None:
    engine = InMemoryGovernanceEngine()
    engine.register_rule(
        GovernanceRule(
            rule_id="rule-disabled",
            name="Disabled Deny",
            description="should be ignored",
            enabled=False,
        ),
        _StaticRule("DENY", reasons=("blocked",)),
    )
    engine.register_rule(
        GovernanceRule(rule_id="rule-enabled", name="Enabled", description="allow"),
        _StaticRule("ALLOW"),
    )

    decision = engine.evaluate(_evidence())

    assert decision.status == "ALLOW"
    assert decision.reasons == ()


def test_governance_decision_module_has_no_forbidden_dependencies() -> None:
    decision_files = (
        _GOVERNANCE_DECISION_ROOT / "models.py",
        _GOVERNANCE_DECISION_ROOT / "rules.py",
        _GOVERNANCE_DECISION_ROOT / "evaluator.py",
        _GOVERNANCE_DECISION_ROOT / "memory_engine.py",
    )
    for path in decision_files:
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

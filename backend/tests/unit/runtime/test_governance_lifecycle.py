# AgentFlow Intelligence v2.0 — Runtime governance lifecycle orchestration tests (Phase 11.11)

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.runtime.audit.models import AuditRecord
from app.runtime.evidence.models import ExecutionEvidence, PermissionDecision
from app.runtime.governance.approval.models import ApprovalDecision
from app.runtime.governance.enforcement.memory_enforcer import InMemoryGovernanceEnforcer
from app.runtime.governance.lifecycle.manager import GovernanceLifecycleManager
from app.runtime.governance.lifecycle.models import GovernanceLifecycleContext
from app.runtime.governance.memory_engine import InMemoryGovernanceEngine
from app.runtime.governance.models import GovernanceDecision, GovernanceRule
from app.runtime.governance.reporting.generator import GovernanceReportGenerator

_LIFECYCLE_ORCHESTRATION_ROOT = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "runtime"
    / "governance"
    / "lifecycle"
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
    "ToolExecutionEngine",
    "AgentRuntime",
    "AgentExecutionPipeline",
    "ExecutionContext",
    "EvidenceCollector",
    "EvidenceQueryService",
)


def _evidence(*, status: str = "COMPLETED", **overrides: object) -> ExecutionEvidence:
    defaults = {
        "evidence_id": "evidence-lifecycle-1",
        "execution_id": "exec-lifecycle-1",
        "agent_id": "agent-lifecycle-1",
        "correlation_id": "corr-lifecycle-1",
        "status": status,
        "audit_records": (
            AuditRecord(
                audit_id="audit-lifecycle-1",
                event_type="execution.start",
                execution_id="exec-lifecycle-1",
                agent_id="agent-lifecycle-1",
                decision="ALLOW",
            ),
        ),
    }
    defaults.update(overrides)
    return ExecutionEvidence(**defaults)  # type: ignore[arg-type]


class _AllowRule:
    def evaluate(self, evidence: ExecutionEvidence) -> GovernanceDecision:
        return GovernanceDecision(
            decision_id="decision-allow",
            execution_id=evidence.execution_id,
            agent_id=evidence.agent_id,
            status="ALLOW",
            reasons=("policy satisfied",),
        )


class _DenyRule:
    def evaluate(self, evidence: ExecutionEvidence) -> GovernanceDecision:
        return GovernanceDecision(
            decision_id="decision-deny",
            execution_id=evidence.execution_id,
            agent_id=evidence.agent_id,
            status="DENY",
            reasons=("permission denied",),
        )


class _WarnRule:
    def evaluate(self, evidence: ExecutionEvidence) -> GovernanceDecision:
        status = "WARN" if evidence.status == "FAILED" else "ALLOW"
        return GovernanceDecision(
            decision_id="decision-warn",
            execution_id=evidence.execution_id,
            agent_id=evidence.agent_id,
            status=status,  # type: ignore[arg-type]
            reasons=("execution anomaly",) if status == "WARN" else (),
        )


def _manager(*, rule: object) -> GovernanceLifecycleManager:
    engine = InMemoryGovernanceEngine()
    engine.register_rule(
        GovernanceRule(rule_id="rule-1", name="Lifecycle Rule", description="test"),
        rule,  # type: ignore[arg-type]
    )
    return GovernanceLifecycleManager(
        decision_engine=engine,
        enforcer=InMemoryGovernanceEnforcer(),
        report_generator=GovernanceReportGenerator(),
    )


def test_lifecycle_context_creation() -> None:
    context = GovernanceLifecycleContext(
        execution_id="exec-lifecycle-1",
        evidence=_evidence(),
        metadata={"phase": "11.11"},
    )

    assert context.execution_id == "exec-lifecycle-1"
    assert context.evidence is not None
    assert context.decision is None
    assert context.metadata["phase"] == "11.11"


def test_lifecycle_models_are_immutable() -> None:
    context = GovernanceLifecycleContext(execution_id="exec-lifecycle-1")

    with pytest.raises(FrozenInstanceError):
        context.execution_id = "changed"  # type: ignore[misc]

    updated = context.with_updates(metadata={"updated": True})
    assert updated.metadata["updated"] is True
    assert context.metadata == {}


def test_evaluation_flow() -> None:
    manager = _manager(rule=_AllowRule())
    context = GovernanceLifecycleContext(
        execution_id="exec-lifecycle-1",
        evidence=_evidence(),
    )

    started = manager.start(context)
    evaluated = manager.evaluate(started)

    assert started.metadata["lifecycle_status"] == "STARTED"
    assert evaluated.decision is not None
    assert evaluated.decision.status == "ALLOW"
    assert evaluated.metadata["lifecycle_status"] == "EVALUATED"


def test_decision_aggregation_via_manager() -> None:
    manager = _manager(rule=_DenyRule())
    context = GovernanceLifecycleContext(
        execution_id="exec-lifecycle-1",
        evidence=_evidence(
            permission_decisions=(
                PermissionDecision(
                    execution_id="exec-lifecycle-1",
                    decision="DENY",
                    tool_name="email.send",
                ),
            )
        ),
    )
    context = manager.start(context)
    evaluated = manager.evaluate(context)

    assert evaluated.decision is not None
    assert evaluated.decision.status == "DENY"
    assert evaluated.decision.reasons == ("permission denied",)


def test_enforcement_mapping() -> None:
    manager = _manager(rule=_DenyRule())
    context = GovernanceLifecycleContext(
        execution_id="exec-lifecycle-1",
        evidence=_evidence(),
    )
    context = manager.evaluate(manager.start(context))
    enforced = manager.apply_action(context)

    assert enforced.action is not None
    assert enforced.action.action_type == "BLOCK"
    assert enforced.action.decision_status == "DENY"
    assert enforced.metadata["lifecycle_status"] == "ENFORCED"


def test_report_generation() -> None:
    manager = _manager(rule=_WarnRule())
    context = GovernanceLifecycleContext(
        execution_id="exec-lifecycle-1",
        evidence=_evidence(status="FAILED"),
    )
    context = manager.evaluate(manager.start(context))
    context = manager.apply_action(context)
    updated, result = manager.generate_report(context)

    assert updated.report is not None
    assert result.report_id == updated.report.report_id
    assert result.decision_status == "WARN"
    assert result.action_type == "WARN"
    assert result.final_status == "WARN"
    assert updated.metadata["lifecycle_status"] == "REPORTED"


def test_approval_optional_path() -> None:
    approval = ApprovalDecision(
        request_id="approval-lifecycle-1",
        decision="APPROVE",
        approver="reviewer-1",
        reason="exception approved",
    )
    manager = _manager(rule=_DenyRule())
    context = GovernanceLifecycleContext(
        execution_id="exec-lifecycle-1",
        evidence=_evidence(),
        approval=approval,
    )
    context = manager.apply_action(manager.evaluate(manager.start(context)))
    _, result = manager.generate_report(context)

    assert result.approval_status == "APPROVED"
    assert result.final_status == "APPROVED_OVERRIDE"


def test_standalone_behavior_does_not_mutate_source_objects() -> None:
    evidence = _evidence()
    manager = _manager(rule=_AllowRule())
    context = GovernanceLifecycleContext(
        execution_id="exec-lifecycle-1",
        evidence=evidence,
    )

    manager.apply_action(manager.evaluate(manager.start(context)))
    _, result = manager.generate_report(
        manager.apply_action(
            manager.evaluate(manager.start(context))
        )
    )

    assert context.decision is None
    assert context.action is None
    assert context.report is None
    assert result.final_status == "ALLOWED"


def test_lifecycle_orchestration_has_no_forbidden_dependencies() -> None:
    orchestration_files = (
        _LIFECYCLE_ORCHESTRATION_ROOT / "models.py",
        _LIFECYCLE_ORCHESTRATION_ROOT / "manager.py",
    )
    for path in orchestration_files:
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

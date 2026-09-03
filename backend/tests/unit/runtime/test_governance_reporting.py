# AgentFlow Intelligence v2.0 — Runtime governance reporting tests (Phase 11.10)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.runtime.audit.models import AuditRecord
from app.runtime.evidence.models import EventSummary, ExecutionEvidence, PermissionDecision
from app.runtime.governance.approval.models import ApprovalDecision
from app.runtime.governance.enforcement.models import GovernanceAction
from app.runtime.governance.models import GovernanceDecision
from app.runtime.governance.reporting.generator import GovernanceReportGenerator
from app.runtime.governance.reporting.memory_store import InMemoryReportStore
from app.runtime.governance.reporting.models import GovernanceReport

_REPORTING_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "reporting"
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
    "GovernanceEvaluator",
    "InMemoryGovernanceEngine",
    "GovernanceEnforcer",
    "AgentRuntime",
    "AgentExecutionPipeline",
    "EvidenceCollector",
    "EvidenceQueryService",
    "ExecutionContext",
    "InMemoryApprovalStore",
)


def _evidence(**overrides: object) -> ExecutionEvidence:
    defaults = {
        "evidence_id": "evidence-report-1",
        "execution_id": "exec-report-1",
        "agent_id": "agent-report-1",
        "correlation_id": "corr-report-1",
        "status": "COMPLETED",
        "audit_records": (
            AuditRecord(
                audit_id="audit-report-1",
                event_type="execution.start",
                execution_id="exec-report-1",
                agent_id="agent-report-1",
                decision="ALLOW",
            ),
        ),
        "event_summary": EventSummary(total_events=2, event_types=("execution.start",)),
    }
    defaults.update(overrides)
    return ExecutionEvidence(**defaults)  # type: ignore[arg-type]


def _decision(*, status: str = "ALLOW") -> GovernanceDecision:
    return GovernanceDecision(
        decision_id="decision-report-1",
        execution_id="exec-report-1",
        agent_id="agent-report-1",
        status=status,  # type: ignore[arg-type]
        reasons=("policy satisfied",) if status == "ALLOW" else ("policy violation",),
    )


def _action(*, action_type: str = "ALLOW", decision_status: str = "ALLOW") -> GovernanceAction:
    return GovernanceAction(
        action_id="action-report-1",
        execution_id="exec-report-1",
        decision_status=decision_status,  # type: ignore[arg-type]
        action_type=action_type,  # type: ignore[arg-type]
        reason="enforcement result",
    )


def _report() -> GovernanceReport:
    return GovernanceReport(
        report_id="report-1",
        execution_id="exec-report-1",
        agent_id="agent-report-1",
        risk_level="LOW",
        decision_status="ALLOW",
        summary="baseline report",
        evidence_count=4,
    )


def test_report_creation() -> None:
    report = _report()

    assert report.report_id == "report-1"
    assert report.execution_id == "exec-report-1"
    assert report.risk_level == "LOW"
    assert report.evidence_count == 4
    assert report.created_at is not None


def test_generator_aggregation() -> None:
    generator = GovernanceReportGenerator()
    evidence = _evidence()
    decision = _decision(status="WARN")
    action = _action(action_type="WARN", decision_status="WARN")
    approval = ApprovalDecision(
        request_id="approval-1",
        decision="APPROVE",
        approver="reviewer-1",
        reason="approved exception",
    )

    report = generator.generate(evidence, decision, action, approval)

    assert report.execution_id == "exec-report-1"
    assert report.agent_id == "agent-report-1"
    assert report.decision_status == "WARN"
    assert report.approval_status == "APPROVED"
    assert report.evidence_count == 4
    assert "decision=WARN" in report.summary
    assert report.metadata["decision_id"] == "decision-report-1"
    assert report.metadata["action_id"] == "action-report-1"


def test_risk_mapping() -> None:
    generator = GovernanceReportGenerator()

    allow_report = generator.generate(
        _evidence(),
        _decision(status="ALLOW"),
        _action(action_type="ALLOW"),
    )
    warn_report = generator.generate(
        _evidence(),
        _decision(status="WARN"),
        _action(action_type="WARN", decision_status="WARN"),
    )
    deny_report = generator.generate(
        _evidence(
            permission_decisions=(
                PermissionDecision(
                    execution_id="exec-report-1",
                    decision="DENY",
                    tool_name="email.send",
                ),
            )
        ),
        _decision(status="DENY"),
        _action(action_type="BLOCK", decision_status="DENY"),
    )
    approved_deny_report = generator.generate(
        _evidence(),
        _decision(status="DENY"),
        _action(action_type="BLOCK", decision_status="DENY"),
        ApprovalDecision(
            request_id="approval-1",
            decision="APPROVE",
            approver="reviewer-1",
            reason="override",
        ),
    )

    assert allow_report.risk_level == "LOW"
    assert warn_report.risk_level == "MEDIUM"
    assert deny_report.risk_level == "CRITICAL"
    assert approved_deny_report.risk_level == "HIGH"


def test_store_create_and_get() -> None:
    store = InMemoryReportStore()
    report = _report()

    store.create(report)

    assert store.get("report-1") == report
    assert store.get("missing") is None


def test_store_list_by_execution() -> None:
    store = InMemoryReportStore()
    store.create(_report())
    store.create(
        GovernanceReport(
            report_id="report-2",
            execution_id="exec-report-1",
            risk_level="MEDIUM",
            decision_status="WARN",
            summary="second report",
            evidence_count=2,
        )
    )
    store.create(
        GovernanceReport(
            report_id="report-3",
            execution_id="exec-report-2",
            risk_level="LOW",
            decision_status="ALLOW",
            summary="other execution",
            evidence_count=1,
        )
    )

    reports = store.list_by_execution("exec-report-1")

    assert len(reports) == 2
    assert {report.report_id for report in reports} == {"report-1", "report-2"}


def test_store_delete() -> None:
    store = InMemoryReportStore()
    store.create(_report())

    store.delete("report-1")

    assert store.get("report-1") is None


def test_report_store_is_thread_safe() -> None:
    store = InMemoryReportStore()
    errors: list[Exception] = []

    def create_many(prefix: str) -> None:
        try:
            for index in range(20):
                store.create(
                    GovernanceReport(
                        report_id=f"report-{prefix}-{index}",
                        execution_id=f"exec-{prefix}-{index}",
                        risk_level="LOW",
                        decision_status="ALLOW",
                        summary="thread test",
                        evidence_count=1,
                    )
                )
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=create_many, args=(f"t{i}",)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert store.get("report-t0-0") is not None


def test_governance_report_is_immutable() -> None:
    report = _report()

    with pytest.raises(FrozenInstanceError):
        report.risk_level = "CRITICAL"  # type: ignore[misc]

    updated = report.with_updates(risk_level="CRITICAL")
    assert updated.risk_level == "CRITICAL"
    assert report.risk_level == "LOW"


def test_reporting_module_has_no_forbidden_dependencies() -> None:
    for path in _REPORTING_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

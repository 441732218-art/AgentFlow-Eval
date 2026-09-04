# AgentFlow Intelligence v2.0 — Governance runtime orchestrator tests (Phase 12.10)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.governance.binding.memory_binder import InMemoryRuntimeEnforcementBinder
from app.runtime.governance.enforcement.models import GovernanceAction
from app.runtime.governance.enforcement_pipeline.memory_pipeline import (
    InMemoryRuntimeEnforcementPipeline,
)
from app.runtime.governance.models import GovernanceDecision
from app.runtime.governance.orchestrator.memory_orchestrator import (
    InMemoryGovernanceRuntimeOrchestrator,
)
from app.runtime.governance.orchestrator.models import (
    GovernanceExecutionRequest,
    GovernanceExecutionResult,
)
from app.runtime.governance.policy_binding.memory_binder import InMemoryPolicyExecutionBinder
from app.runtime.governance.reporting.generator import GovernanceReportGenerator
from app.runtime.governance.routing.memory_router import InMemoryGovernanceDecisionRouter
from app.runtime.governance.versioning.memory_registry import InMemoryGovernancePolicyRegistry
from app.runtime.governance.versioning.models import GovernancePolicyVersion

_ORCHESTRATOR_ROOT = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "runtime"
    / "governance"
    / "orchestrator"
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


def _request(
    *,
    decision_status: str,
    execution_id: str = "exec-orchestrator-1",
    enforcement_status: str | None = None,
    policy_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> GovernanceExecutionRequest:
    return GovernanceExecutionRequest(
        execution_id=execution_id,
        decision_status=decision_status,
        enforcement_status=enforcement_status,
        policy_id=policy_id,
        metadata=dict(metadata or {"agent_id": "agent-orchestrator-1"}),
    )


def _evidence() -> ExecutionEvidence:
    return ExecutionEvidence(
        evidence_id="evidence-orchestrator-1",
        execution_id="exec-orchestrator-1",
        agent_id="agent-orchestrator-1",
        correlation_id="corr-1",
        status="COMPLETED",
    )


def _decision(*, status: str = "ALLOW") -> GovernanceDecision:
    return GovernanceDecision(
        decision_id="decision-orchestrator-1",
        execution_id="exec-orchestrator-1",
        agent_id="agent-orchestrator-1",
        status=status,  # type: ignore[arg-type]
        evaluated_at=datetime(2026, 9, 4, 8, 0, tzinfo=timezone.utc),
    )


def _action(*, action_type: str = "ALLOW") -> GovernanceAction:
    return GovernanceAction(
        action_id="action-orchestrator-1",
        execution_id="exec-orchestrator-1",
        decision_status="ALLOW",
        action_type=action_type,  # type: ignore[arg-type]
        reason="orchestrator test action",
    )


def test_governance_execution_request_creation() -> None:
    request = _request(decision_status="ALLOW", policy_id="policy-1")

    assert request.execution_id == "exec-orchestrator-1"
    assert request.decision_status == "ALLOW"
    assert request.policy_id == "policy-1"


def test_governance_execution_result_is_immutable() -> None:
    result = GovernanceExecutionResult(
        execution_id="exec-orchestrator-1",
        route_type="ALLOW",
        action="CONTINUE",
        enforcement_applied=False,
        approval_required=False,
        blocked=False,
        report_generated=False,
    )

    with pytest.raises(FrozenInstanceError):
        result.blocked = True  # type: ignore[misc]

    updated = result.with_updates(blocked=True)
    assert updated.blocked is True
    assert result.blocked is False


def test_orchestrator_routes_allow_with_router_only() -> None:
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(
        decision_router=InMemoryGovernanceDecisionRouter(),
    )
    result = orchestrator.execute(_request(decision_status="ALLOW"))

    assert result.route_type == "ALLOW"
    assert result.action == "CONTINUE"
    assert result.blocked is False
    assert result.approval_required is False


def test_orchestrator_routes_warn() -> None:
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(
        decision_router=InMemoryGovernanceDecisionRouter(),
    )
    result = orchestrator.execute(_request(decision_status="WARN"))

    assert result.route_type == "WARNING"
    assert result.action == "CONTINUE_WITH_WARNING"


def test_orchestrator_routes_require_approval() -> None:
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(
        decision_router=InMemoryGovernanceDecisionRouter(),
    )
    result = orchestrator.execute(_request(decision_status="REQUIRE_APPROVAL"))

    assert result.route_type == "APPROVAL"
    assert result.action == "WAIT_APPROVAL"
    assert result.approval_required is True


def test_orchestrator_routes_deny_as_block() -> None:
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(
        decision_router=InMemoryGovernanceDecisionRouter(),
    )
    result = orchestrator.execute(_request(decision_status="DENY"))

    assert result.route_type == "BLOCK"
    assert result.action == "BLOCK"
    assert result.blocked is True


def test_orchestrator_coordinates_enforcement_pipeline() -> None:
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(
        decision_router=InMemoryGovernanceDecisionRouter(),
        enforcement_pipeline=InMemoryRuntimeEnforcementPipeline(),
    )
    result = orchestrator.execute(_request(decision_status="ALLOW", enforcement_status="ALLOW"))

    assert result.enforcement_applied is True
    assert result.metadata["enforcement_status"] == "ALLOW"


def test_orchestrator_coordinates_enforcement_binding() -> None:
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(
        decision_router=InMemoryGovernanceDecisionRouter(),
        enforcement_pipeline=InMemoryRuntimeEnforcementPipeline(),
        enforcement_binder=InMemoryRuntimeEnforcementBinder(),
    )
    result = orchestrator.execute(_request(decision_status="WARN"))

    assert result.enforcement_applied is True
    assert result.metadata["runtime_binding_decision"] == "WARN"


def test_orchestrator_coordinates_policy_binding() -> None:
    registry = InMemoryGovernancePolicyRegistry()
    registry.register(
        GovernancePolicyVersion(
            policy_id="policy-1",
            version="1.0.0",
            name="Orchestrator Policy",
            status="ACTIVE",
        )
    )
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(
        decision_router=InMemoryGovernanceDecisionRouter(),
        policy_binder=InMemoryPolicyExecutionBinder(policy_registry=registry),
    )
    result = orchestrator.execute(
        _request(
            decision_status="ALLOW",
            policy_id="policy-1",
            metadata={"agent_id": "agent-orchestrator-1", "policy_version": "1.0.0"},
        )
    )

    assert result.metadata["policy_binding_status"] == "BOUND"


def test_orchestrator_generates_report_when_artifacts_provided() -> None:
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(
        decision_router=InMemoryGovernanceDecisionRouter(),
        report_generator=GovernanceReportGenerator(),
    )
    result = orchestrator.execute(
        _request(
            decision_status="ALLOW",
            metadata={
                "agent_id": "agent-orchestrator-1",
                "evidence": _evidence(),
                "governance_decision": _decision(),
                "governance_action": _action(),
            },
        )
    )

    assert result.report_generated is True
    assert "report_id" in result.metadata


def test_orchestrator_disabled_behavior() -> None:
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(
        enabled=False,
        decision_router=InMemoryGovernanceDecisionRouter(),
    )
    result = orchestrator.execute(_request(decision_status="DENY", enforcement_status="BLOCK"))

    assert result.route_type == "ALLOW"
    assert result.action == "CONTINUE"
    assert result.enforcement_applied is False
    assert result.report_generated is False
    assert result.metadata["orchestration_enabled"] is False


def test_orchestrator_list_get_and_clear_results() -> None:
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(
        decision_router=InMemoryGovernanceDecisionRouter(),
    )
    orchestrator.execute(_request(decision_status="ALLOW", execution_id="exec-a"))
    latest = orchestrator.execute(_request(decision_status="WARN", execution_id="exec-a"))

    assert len(orchestrator.list_results()) == 2
    assert len(orchestrator.list_results(execution_id="exec-a")) == 2
    assert orchestrator.get_result("exec-a") == latest

    orchestrator.clear()

    assert orchestrator.list_results() == []
    assert orchestrator.get_result("exec-a") is None


def test_orchestrator_fallback_without_router() -> None:
    orchestrator = InMemoryGovernanceRuntimeOrchestrator()
    result = orchestrator.execute(_request(decision_status="REQUIRE_APPROVAL"))

    assert result.route_type == "APPROVAL"
    assert result.action == "WAIT_APPROVAL"
    assert result.approval_required is True


def test_orchestrator_preserves_metadata() -> None:
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(
        decision_router=InMemoryGovernanceDecisionRouter(),
    )
    result = orchestrator.execute(
        _request(
            decision_status="WARN",
            policy_id="policy-1",
            metadata={"correlation_id": "corr-1", "tool_name": "probe.echo"},
        )
    )

    assert result.metadata["correlation_id"] == "corr-1"
    assert result.metadata["tool_name"] == "probe.echo"
    assert result.metadata["policy_id"] == "policy-1"
    assert result.metadata["observation_only"] is True


def test_orchestrator_is_thread_safe() -> None:
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(
        decision_router=InMemoryGovernanceDecisionRouter(),
    )
    errors: list[Exception] = []
    statuses = ("ALLOW", "WARN", "REQUIRE_APPROVAL", "DENY")

    def worker(index: int) -> None:
        try:
            orchestrator.execute(
                _request(
                    decision_status=statuses[index % len(statuses)],
                    execution_id=f"exec-thread-{index}",
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
    assert len(orchestrator.list_results()) == 24


def test_governance_orchestrator_has_no_forbidden_dependencies() -> None:
    for path in _ORCHESTRATOR_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

# AgentFlow Intelligence v2.0 — Runtime governance decision gateway tests (Phase 12.5)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.runtime.governance.control.models import GovernanceControlDecision
from app.runtime.governance.gateway.memory_gateway import InMemoryGovernanceDecisionGateway
from app.runtime.governance.gateway.models import GovernanceGateRequest, GovernanceGateResult

_GATEWAY_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "gateway"
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


def _control_decision(
    *,
    decision_status: str,
    action_type: str | None = None,
    execution_id: str = "exec-gateway-1",
    reason: str = "control reason",
) -> GovernanceControlDecision:
    return GovernanceControlDecision(
        control_id="control-gateway-1",
        execution_id=execution_id,
        decision_status=decision_status,  # type: ignore[arg-type]
        action_type=action_type or decision_status,  # type: ignore[arg-type]
        reason=reason,
        timestamp=datetime(2026, 9, 4, 4, 0, tzinfo=timezone.utc),
        metadata={"source": "test"},
    )


def _request(
    *,
    decision_status: str,
    execution_id: str = "exec-gateway-1",
    tool_name: str = "probe.echo",
    metadata: dict[str, object] | None = None,
) -> GovernanceGateRequest:
    return GovernanceGateRequest(
        execution_id=execution_id,
        agent_id="agent-gateway-1",
        tool_name=tool_name,
        decision_id="decision-gateway-1",
        control_decision=_control_decision(
            decision_status=decision_status,
            execution_id=execution_id,
        ),
        metadata=dict(metadata or {"phase": "tool"}),
    )


def test_governance_gate_request_is_immutable() -> None:
    request = _request(decision_status="ALLOW")

    with pytest.raises(FrozenInstanceError):
        request.tool_name = "other.tool"  # type: ignore[misc]

    updated = request.with_updates(tool_name="other.tool")
    assert updated.tool_name == "other.tool"
    assert request.tool_name == "probe.echo"


def test_governance_gate_result_is_immutable() -> None:
    result = GovernanceGateResult(
        gate_id="gate-1",
        execution_id="exec-gateway-1",
        status="ALLOW",
        reason="all clear",
    )

    with pytest.raises(FrozenInstanceError):
        result.status = "BLOCK"  # type: ignore[misc]

    updated = result.with_updates(status="BLOCK")
    assert updated.status == "BLOCK"
    assert result.status == "ALLOW"


def test_allow_control_maps_to_allow_gate_result() -> None:
    gateway = InMemoryGovernanceDecisionGateway()
    result = gateway.evaluate(_request(decision_status="ALLOW"))

    assert result.status == "ALLOW"
    assert result.execution_id == "exec-gateway-1"
    assert result.reason == "control reason"


def test_warn_control_maps_to_warn_gate_result() -> None:
    gateway = InMemoryGovernanceDecisionGateway()
    request = replace(
        _request(decision_status="WARN"),
        control_decision=_control_decision(
            decision_status="WARN",
            reason="risk detected",
        ),
    )

    result = gateway.evaluate(request)

    assert result.status == "WARN"
    assert result.reason == "risk detected"


def test_block_control_maps_to_block_gate_result() -> None:
    gateway = InMemoryGovernanceDecisionGateway()
    request = replace(
        _request(decision_status="BLOCK"),
        control_decision=_control_decision(
            decision_status="BLOCK",
            reason="policy violation",
        ),
    )

    result = gateway.evaluate(request)

    assert result.status == "BLOCK"
    assert result.reason == "policy violation"


def test_require_approval_control_maps_to_require_approval_gate_result() -> None:
    gateway = InMemoryGovernanceDecisionGateway()
    request = replace(
        _request(decision_status="REQUIRE_APPROVAL"),
        control_decision=_control_decision(
            decision_status="REQUIRE_APPROVAL",
            action_type="REQUIRE_APPROVAL",
            reason="approval required",
        ),
    )

    result = gateway.evaluate(request)

    assert result.status == "REQUIRE_APPROVAL"
    assert result.reason == "approval required"


def test_evaluate_records_gateway_results() -> None:
    gateway = InMemoryGovernanceDecisionGateway()
    gateway.evaluate(_request(decision_status="ALLOW"))
    gateway.evaluate(_request(decision_status="BLOCK", execution_id="exec-gateway-2"))

    records = gateway.list_results()
    assert len(records) == 2
    assert {record.execution_id for record in records} == {
        "exec-gateway-1",
        "exec-gateway-2",
    }


def test_list_results_filters_by_execution_id() -> None:
    gateway = InMemoryGovernanceDecisionGateway()
    gateway.evaluate(_request(decision_status="ALLOW", execution_id="exec-a"))
    gateway.evaluate(_request(decision_status="WARN", execution_id="exec-b"))

    filtered = gateway.list_results(execution_id="exec-a")
    assert len(filtered) == 1
    assert filtered[0].execution_id == "exec-a"


def test_clear_removes_recorded_results() -> None:
    gateway = InMemoryGovernanceDecisionGateway()
    gateway.evaluate(_request(decision_status="ALLOW"))

    gateway.clear()

    assert gateway.list_results() == []


def test_disabled_gateway_returns_allow_without_blocking() -> None:
    gateway = InMemoryGovernanceDecisionGateway(enabled=False)
    result = gateway.evaluate(_request(decision_status="BLOCK"))

    assert result.status == "ALLOW"
    assert result.reason == "gateway evaluation disabled"
    assert result.metadata["gateway_enabled"] is False


def test_metadata_propagates_from_request_and_control_decision() -> None:
    gateway = InMemoryGovernanceDecisionGateway()
    result = gateway.evaluate(
        _request(
            decision_status="WARN",
            metadata={"correlation_id": "corr-1"},
        )
    )

    assert result.metadata["agent_id"] == "agent-gateway-1"
    assert result.metadata["tool_name"] == "probe.echo"
    assert result.metadata["decision_id"] == "decision-gateway-1"
    assert result.metadata["control_id"] == "control-gateway-1"
    assert result.metadata["control_status"] == "WARN"
    assert result.metadata["gate_status"] == "WARN"
    assert result.metadata["correlation_id"] == "corr-1"
    assert result.metadata["source"] == "test"


def test_gateway_is_thread_safe() -> None:
    gateway = InMemoryGovernanceDecisionGateway()
    errors: list[Exception] = []
    statuses = ("ALLOW", "WARN", "BLOCK", "REQUIRE_APPROVAL")

    def worker(index: int) -> None:
        try:
            gateway.evaluate(
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
    assert len(gateway.list_results()) == 24


def test_unsupported_control_status_raises() -> None:
    gateway = InMemoryGovernanceDecisionGateway()
    request = replace(
        _request(decision_status="ALLOW"),
        control_decision=replace(
            _control_decision(decision_status="ALLOW"),
            decision_status="UNKNOWN",  # type: ignore[arg-type]
        ),
    )

    with pytest.raises(ValueError, match="Unsupported governance control decision status"):
        gateway.evaluate(request)


def test_governance_gateway_has_no_forbidden_dependencies() -> None:
    for path in _GATEWAY_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

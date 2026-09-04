# AgentFlow Intelligence v2.0 — Runtime enforcement pipeline tests (Phase 12.6)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.runtime.governance.enforcement_pipeline.memory_pipeline import (
    InMemoryRuntimeEnforcementPipeline,
)
from app.runtime.governance.enforcement_pipeline.models import (
    EnforcementRequest,
    EnforcementResult,
)
from app.runtime.governance.gateway.models import GovernanceGateResult

_PIPELINE_ROOT = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "runtime"
    / "governance"
    / "enforcement_pipeline"
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


def _gate_result(
    *,
    status: str,
    execution_id: str = "exec-enforcement-1",
    reason: str = "gate reason",
) -> GovernanceGateResult:
    return GovernanceGateResult(
        gate_id="gate-enforcement-1",
        execution_id=execution_id,
        status=status,  # type: ignore[arg-type]
        reason=reason,
        timestamp=datetime(2026, 9, 4, 5, 0, tzinfo=timezone.utc),
        metadata={"agent_id": "agent-enforcement-1", "tool_name": "probe.echo"},
    )


def _request(
    *,
    status: str,
    execution_id: str = "exec-enforcement-1",
    context: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> EnforcementRequest:
    return EnforcementRequest(
        execution_id=execution_id,
        gate_result=_gate_result(status=status, execution_id=execution_id),
        context=dict(context or {"phase": "tool"}),
        metadata=dict(metadata or {"source": "test"}),
    )


def test_enforcement_request_is_immutable() -> None:
    request = _request(status="ALLOW")

    with pytest.raises(FrozenInstanceError):
        request.execution_id = "other-exec"  # type: ignore[misc]

    updated = request.with_updates(execution_id="other-exec")
    assert updated.execution_id == "other-exec"
    assert request.execution_id == "exec-enforcement-1"


def test_enforcement_result_is_immutable() -> None:
    result = EnforcementResult(
        enforcement_id="enforcement-1",
        execution_id="exec-enforcement-1",
        status="ALLOW",
        reason="all clear",
    )

    with pytest.raises(FrozenInstanceError):
        result.status = "BLOCK"  # type: ignore[misc]

    updated = result.with_updates(status="BLOCK")
    assert updated.status == "BLOCK"
    assert result.status == "ALLOW"


def test_allow_gate_maps_to_allow_enforcement() -> None:
    pipeline = InMemoryRuntimeEnforcementPipeline()
    result = pipeline.evaluate(_request(status="ALLOW"))

    assert result.status == "ALLOW"
    assert result.execution_id == "exec-enforcement-1"
    assert result.reason == "gate reason"


def test_warn_gate_maps_to_warn_enforcement() -> None:
    pipeline = InMemoryRuntimeEnforcementPipeline()
    request = replace(
        _request(status="WARN"),
        gate_result=_gate_result(status="WARN", reason="risk detected"),
    )

    result = pipeline.evaluate(request)

    assert result.status == "WARN"
    assert result.reason == "risk detected"


def test_block_gate_maps_to_block_enforcement() -> None:
    pipeline = InMemoryRuntimeEnforcementPipeline()
    request = replace(
        _request(status="BLOCK"),
        gate_result=_gate_result(status="BLOCK", reason="policy violation"),
    )

    result = pipeline.evaluate(request)

    assert result.status == "BLOCK"
    assert result.reason == "policy violation"


def test_require_approval_gate_maps_to_pending_approval() -> None:
    pipeline = InMemoryRuntimeEnforcementPipeline()
    request = replace(
        _request(status="REQUIRE_APPROVAL"),
        gate_result=_gate_result(status="REQUIRE_APPROVAL", reason="approval required"),
    )

    result = pipeline.evaluate(request)

    assert result.status == "PENDING_APPROVAL"
    assert result.reason == "approval required"


def test_evaluate_records_enforcement_results() -> None:
    pipeline = InMemoryRuntimeEnforcementPipeline()
    pipeline.evaluate(_request(status="ALLOW"))
    pipeline.evaluate(_request(status="BLOCK", execution_id="exec-enforcement-2"))

    records = pipeline.list_results()
    assert len(records) == 2
    assert {record.execution_id for record in records} == {
        "exec-enforcement-1",
        "exec-enforcement-2",
    }


def test_list_results_filters_by_execution_id() -> None:
    pipeline = InMemoryRuntimeEnforcementPipeline()
    pipeline.evaluate(_request(status="ALLOW", execution_id="exec-a"))
    pipeline.evaluate(_request(status="WARN", execution_id="exec-b"))

    filtered = pipeline.list_results(execution_id="exec-a")
    assert len(filtered) == 1
    assert filtered[0].execution_id == "exec-a"


def test_clear_removes_recorded_results() -> None:
    pipeline = InMemoryRuntimeEnforcementPipeline()
    pipeline.evaluate(_request(status="ALLOW"))

    pipeline.clear()

    assert pipeline.list_results() == []


def test_disabled_pipeline_returns_allow_without_blocking() -> None:
    pipeline = InMemoryRuntimeEnforcementPipeline(enabled=False)
    result = pipeline.evaluate(_request(status="BLOCK"))

    assert result.status == "ALLOW"
    assert result.reason == "enforcement pipeline disabled"
    assert result.metadata["enforcement_enabled"] is False


def test_metadata_propagates_from_request_gate_and_context() -> None:
    pipeline = InMemoryRuntimeEnforcementPipeline()
    result = pipeline.evaluate(
        _request(
            status="WARN",
            context={"step_id": "step-1"},
            metadata={"correlation_id": "corr-1"},
        )
    )

    assert result.metadata["gate_id"] == "gate-enforcement-1"
    assert result.metadata["gate_status"] == "WARN"
    assert result.metadata["enforcement_status"] == "WARN"
    assert result.metadata["context"] == {"step_id": "step-1"}
    assert result.metadata["correlation_id"] == "corr-1"
    assert result.metadata["agent_id"] == "agent-enforcement-1"
    assert result.metadata["tool_name"] == "probe.echo"


def test_pipeline_is_thread_safe() -> None:
    pipeline = InMemoryRuntimeEnforcementPipeline()
    errors: list[Exception] = []
    statuses = ("ALLOW", "WARN", "BLOCK", "REQUIRE_APPROVAL")

    def worker(index: int) -> None:
        try:
            pipeline.evaluate(
                _request(
                    status=statuses[index % len(statuses)],
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
    assert len(pipeline.list_results()) == 24


def test_unsupported_gate_status_raises() -> None:
    pipeline = InMemoryRuntimeEnforcementPipeline()
    request = replace(
        _request(status="ALLOW"),
        gate_result=replace(
            _gate_result(status="ALLOW"),
            status="UNKNOWN",  # type: ignore[arg-type]
        ),
    )

    with pytest.raises(ValueError, match="Unsupported governance gate status"):
        pipeline.evaluate(request)


def test_enforcement_pipeline_has_no_forbidden_dependencies() -> None:
    for path in _PIPELINE_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

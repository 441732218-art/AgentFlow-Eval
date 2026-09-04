# AgentFlow Intelligence v2.0 — Runtime enforcement binding tests (Phase 12.7)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.runtime.governance.binding.memory_binder import InMemoryRuntimeEnforcementBinder
from app.runtime.governance.binding.models import RuntimeBindingRequest, RuntimeBindingResult
from app.runtime.governance.enforcement_pipeline.models import EnforcementResult

_BINDING_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "binding"
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


def _enforcement_result(
    *,
    status: str,
    execution_id: str = "exec-binding-1",
    reason: str = "enforcement reason",
) -> EnforcementResult:
    return EnforcementResult(
        enforcement_id="enforcement-binding-1",
        execution_id=execution_id,
        status=status,  # type: ignore[arg-type]
        reason=reason,
        timestamp=datetime(2026, 9, 4, 6, 0, tzinfo=timezone.utc),
        metadata={"agent_id": "agent-binding-1", "tool_name": "probe.echo"},
    )


def _request(
    *,
    status: str,
    execution_id: str = "exec-binding-1",
    runtime_context: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> RuntimeBindingRequest:
    return RuntimeBindingRequest(
        execution_id=execution_id,
        enforcement_result=_enforcement_result(status=status, execution_id=execution_id),
        runtime_context=dict(runtime_context or {"phase": "tool"}),
        metadata=dict(metadata or {"source": "test"}),
    )


def test_runtime_binding_request_is_immutable() -> None:
    request = _request(status="ALLOW")

    with pytest.raises(FrozenInstanceError):
        request.execution_id = "other-exec"  # type: ignore[misc]

    updated = request.with_updates(execution_id="other-exec")
    assert updated.execution_id == "other-exec"
    assert request.execution_id == "exec-binding-1"


def test_runtime_binding_result_is_immutable() -> None:
    result = RuntimeBindingResult(
        binding_id="binding-1",
        execution_id="exec-binding-1",
        decision="ALLOW",
        applied=True,
        reason="all clear",
    )

    with pytest.raises(FrozenInstanceError):
        result.applied = False  # type: ignore[misc]

    updated = result.with_updates(applied=False)
    assert updated.applied is False
    assert result.applied is True


def test_allow_enforcement_maps_to_allow_binding() -> None:
    binder = InMemoryRuntimeEnforcementBinder()
    result = binder.bind(_request(status="ALLOW"))

    assert result.decision == "ALLOW"
    assert result.applied is True
    assert result.execution_id == "exec-binding-1"
    assert result.reason == "enforcement reason"


def test_warn_enforcement_maps_to_warn_binding() -> None:
    binder = InMemoryRuntimeEnforcementBinder()
    request = replace(
        _request(status="WARN"),
        enforcement_result=_enforcement_result(status="WARN", reason="risk detected"),
    )

    result = binder.bind(request)

    assert result.decision == "WARN"
    assert result.applied is True
    assert result.reason == "risk detected"


def test_block_enforcement_maps_to_block_binding() -> None:
    binder = InMemoryRuntimeEnforcementBinder()
    request = replace(
        _request(status="BLOCK"),
        enforcement_result=_enforcement_result(status="BLOCK", reason="policy violation"),
    )

    result = binder.bind(request)

    assert result.decision == "BLOCK"
    assert result.applied is True
    assert result.reason == "policy violation"
    assert result.metadata["observation_only"] is True


def test_pending_approval_enforcement_maps_to_pending_approval_binding() -> None:
    binder = InMemoryRuntimeEnforcementBinder()
    request = replace(
        _request(status="PENDING_APPROVAL"),
        enforcement_result=_enforcement_result(
            status="PENDING_APPROVAL",
            reason="approval required",
        ),
    )

    result = binder.bind(request)

    assert result.decision == "PENDING_APPROVAL"
    assert result.applied is True
    assert result.reason == "approval required"


def test_bind_records_binding_history() -> None:
    binder = InMemoryRuntimeEnforcementBinder()
    binder.bind(_request(status="ALLOW"))
    binder.bind(_request(status="BLOCK", execution_id="exec-binding-2"))

    records = binder.list_bindings()
    assert len(records) == 2
    assert {record.execution_id for record in records} == {
        "exec-binding-1",
        "exec-binding-2",
    }


def test_list_bindings_filters_by_execution_id() -> None:
    binder = InMemoryRuntimeEnforcementBinder()
    binder.bind(_request(status="ALLOW", execution_id="exec-a"))
    binder.bind(_request(status="WARN", execution_id="exec-b"))

    filtered = binder.list_bindings(execution_id="exec-a")
    assert len(filtered) == 1
    assert filtered[0].execution_id == "exec-a"


def test_clear_removes_recorded_bindings() -> None:
    binder = InMemoryRuntimeEnforcementBinder()
    binder.bind(_request(status="ALLOW"))

    binder.clear()

    assert binder.list_bindings() == []


def test_disabled_binder_returns_allow_without_applying() -> None:
    binder = InMemoryRuntimeEnforcementBinder(enabled=False)
    result = binder.bind(_request(status="BLOCK"))

    assert result.decision == "ALLOW"
    assert result.applied is False
    assert result.reason == "enforcement binding disabled"
    assert result.metadata["binding_enabled"] is False


def test_metadata_propagates_from_request_enforcement_and_runtime_context() -> None:
    binder = InMemoryRuntimeEnforcementBinder()
    result = binder.bind(
        _request(
            status="WARN",
            runtime_context={"step_id": "step-1"},
            metadata={"correlation_id": "corr-1"},
        )
    )

    assert result.metadata["enforcement_id"] == "enforcement-binding-1"
    assert result.metadata["enforcement_status"] == "WARN"
    assert result.metadata["binding_decision"] == "WARN"
    assert result.metadata["runtime_context"] == {"step_id": "step-1"}
    assert result.metadata["correlation_id"] == "corr-1"
    assert result.metadata["agent_id"] == "agent-binding-1"
    assert result.metadata["observation_only"] is True


def test_binder_is_thread_safe() -> None:
    binder = InMemoryRuntimeEnforcementBinder()
    errors: list[Exception] = []
    statuses = ("ALLOW", "WARN", "BLOCK", "PENDING_APPROVAL")

    def worker(index: int) -> None:
        try:
            binder.bind(
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
    assert len(binder.list_bindings()) == 24


def test_unsupported_enforcement_status_raises() -> None:
    binder = InMemoryRuntimeEnforcementBinder()
    request = replace(
        _request(status="ALLOW"),
        enforcement_result=replace(
            _enforcement_result(status="ALLOW"),
            status="UNKNOWN",  # type: ignore[arg-type]
        ),
    )

    with pytest.raises(ValueError, match="Unsupported enforcement result status"):
        binder.bind(request)


def test_enforcement_binding_has_no_forbidden_dependencies() -> None:
    for path in _BINDING_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

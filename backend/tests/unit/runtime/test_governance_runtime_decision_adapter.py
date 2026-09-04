# AgentFlow Intelligence v2.0 — Governance runtime decision adapter tests (Phase 13.3)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.runtime.governance.runtime_adapter.memory_adapter import (
    InMemoryGovernanceRuntimeDecisionAdapter,
)
from app.runtime.governance.runtime_adapter.models import (
    GovernanceRuntimeDecisionRequest,
    GovernanceRuntimeDecisionResult,
)

_ADAPTER_ROOT = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "runtime"
    / "governance"
    / "runtime_adapter"
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
    decision_id: str = "decision-adapter-1",
    execution_id: str = "exec-adapter-1",
    metadata: dict[str, object] | None = None,
) -> GovernanceRuntimeDecisionRequest:
    return GovernanceRuntimeDecisionRequest(
        decision_id=decision_id,
        execution_id=execution_id,
        decision_status=decision_status,  # type: ignore[arg-type]
        target="execution:exec-adapter-1",
        reason="governance decision",
        agent_id="agent-adapter-1",
        evidence_reference="evidence-adapter-1",
        metadata=dict(metadata or {"source": "test"}),
    )


def test_governance_runtime_decision_request_is_immutable() -> None:
    request = _request(decision_status="ALLOW")

    with pytest.raises(FrozenInstanceError):
        request.execution_id = "other-exec"  # type: ignore[misc]

    updated = request.with_updates(execution_id="other-exec")
    assert updated.execution_id == "other-exec"
    assert request.execution_id == "exec-adapter-1"


def test_governance_runtime_decision_result_is_immutable() -> None:
    adapter = InMemoryGovernanceRuntimeDecisionAdapter()
    result = adapter.adapt(_request(decision_status="ALLOW"))

    with pytest.raises(FrozenInstanceError):
        result.executable = False  # type: ignore[misc]

    updated = result.with_updates(executable=False)
    assert updated.executable is False
    assert result.executable is True


def test_allow_maps_to_allow_effect_and_continue_resolution() -> None:
    adapter = InMemoryGovernanceRuntimeDecisionAdapter()
    result = adapter.adapt(_request(decision_status="ALLOW"))

    assert result.effect_action_type == "ALLOW"
    assert result.effect.action_type == "ALLOW"
    assert result.resolution_type == "CONTINUE"
    assert result.executable is True


def test_warn_maps_to_warn_effect_and_continue_with_warning() -> None:
    adapter = InMemoryGovernanceRuntimeDecisionAdapter()
    result = adapter.adapt(_request(decision_status="WARN"))

    assert result.effect_action_type == "WARN"
    assert result.resolution_type == "CONTINUE_WITH_WARNING"
    assert result.executable is True


def test_deny_maps_to_block_effect_and_block_request() -> None:
    adapter = InMemoryGovernanceRuntimeDecisionAdapter()
    result = adapter.adapt(_request(decision_status="DENY"))

    assert result.effect_action_type == "BLOCK"
    assert result.effect.action_type == "BLOCK"
    assert result.resolution_type == "BLOCK_REQUEST"
    assert result.executable is False


def test_block_maps_to_block_effect_and_block_request() -> None:
    adapter = InMemoryGovernanceRuntimeDecisionAdapter()
    result = adapter.adapt(_request(decision_status="BLOCK"))

    assert result.effect_action_type == "BLOCK"
    assert result.resolution_type == "BLOCK_REQUEST"
    assert result.executable is False


def test_require_approval_maps_to_require_approval_effect_and_wait_approval() -> None:
    adapter = InMemoryGovernanceRuntimeDecisionAdapter()
    result = adapter.adapt(_request(decision_status="REQUIRE_APPROVAL"))

    assert result.effect_action_type == "REQUIRE_APPROVAL"
    assert result.resolution_type == "WAIT_APPROVAL"
    assert result.executable is False


def test_metadata_is_preserved_on_effect_and_result() -> None:
    adapter = InMemoryGovernanceRuntimeDecisionAdapter()
    result = adapter.adapt(
        _request(
            decision_status="WARN",
            metadata={"correlation_id": "corr-1", "tool_name": "probe.echo"},
        )
    )

    assert result.metadata["correlation_id"] == "corr-1"
    assert result.metadata["tool_name"] == "probe.echo"
    assert result.effect.metadata["correlation_id"] == "corr-1"
    assert result.effect.evidence_reference == "evidence-adapter-1"
    assert result.metadata["observation_only"] is True


def test_get_list_and_clear_results() -> None:
    adapter = InMemoryGovernanceRuntimeDecisionAdapter()
    first = adapter.adapt(_request(decision_status="ALLOW", decision_id="decision-a"))
    second = adapter.adapt(_request(decision_status="WARN", decision_id="decision-b"))

    assert adapter.get_result(first.result_id) == first
    assert len(adapter.list_results()) == 2

    adapter.clear()

    assert adapter.list_results() == []
    assert adapter.get_result(first.result_id) is None


def test_disabled_behavior_returns_allow_continue() -> None:
    adapter = InMemoryGovernanceRuntimeDecisionAdapter(enabled=False)
    result = adapter.adapt(_request(decision_status="DENY"))

    assert result.effect_action_type == "ALLOW"
    assert result.resolution_type == "CONTINUE"
    assert result.executable is True
    assert result.effect.reason == "governance runtime decision adapter disabled"
    assert result.metadata["adapter_enabled"] is False


def test_unsupported_decision_status_raises() -> None:
    adapter = InMemoryGovernanceRuntimeDecisionAdapter()
    request = _request(decision_status="ALLOW").with_updates(
        decision_status="UNKNOWN",  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="Unsupported governance decision status"):
        adapter.adapt(request)


def test_adapter_is_thread_safe() -> None:
    adapter = InMemoryGovernanceRuntimeDecisionAdapter()
    errors: list[Exception] = []
    statuses = ("ALLOW", "WARN", "DENY", "REQUIRE_APPROVAL")

    def worker(index: int) -> None:
        try:
            adapter.adapt(
                _request(
                    decision_status=statuses[index % len(statuses)],
                    decision_id=f"decision-thread-{index}",
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
    assert len(adapter.list_results()) == 24


def test_governance_runtime_decision_adapter_has_no_forbidden_dependencies() -> None:
    for path in _ADAPTER_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

# AgentFlow Intelligence v2.0 — Policy execution binding tests (Phase 12.8)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.runtime.governance.policy_binding.memory_binder import InMemoryPolicyExecutionBinder
from app.runtime.governance.policy_binding.models import PolicyBindingRequest, PolicyBindingResult
from app.runtime.governance.versioning.memory_registry import InMemoryGovernancePolicyRegistry
from app.runtime.governance.versioning.models import GovernancePolicyVersion

_BINDING_ROOT = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "runtime"
    / "governance"
    / "policy_binding"
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


def _request(
    *,
    policy_id: str = "policy-1",
    policy_version: str = "1.0.0",
    execution_id: str = "exec-policy-bind-1",
    agent_id: str = "agent-policy-bind-1",
    runtime_context: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> PolicyBindingRequest:
    return PolicyBindingRequest(
        policy_id=policy_id,
        policy_version=policy_version,
        execution_id=execution_id,
        agent_id=agent_id,
        runtime_context=dict(runtime_context or {"phase": "execution"}),
        metadata=dict(metadata or {"source": "test"}),
    )


def _active_policy(
    *,
    policy_id: str = "policy-1",
    version: str = "1.0.0",
) -> GovernancePolicyVersion:
    return GovernancePolicyVersion(
        policy_id=policy_id,
        version=version,
        name="Test Policy",
        description="Policy for binding tests",
        status="ACTIVE",
    )


def test_policy_binding_request_is_immutable() -> None:
    request = _request()

    with pytest.raises(FrozenInstanceError):
        request.policy_id = "other-policy"  # type: ignore[misc]

    updated = request.with_updates(policy_id="other-policy")
    assert updated.policy_id == "other-policy"
    assert request.policy_id == "policy-1"


def test_policy_binding_result_is_immutable() -> None:
    result = PolicyBindingResult(
        binding_id="binding-1",
        policy_id="policy-1",
        policy_version="1.0.0",
        execution_id="exec-policy-bind-1",
        status="BOUND",
        applied=True,
    )

    with pytest.raises(FrozenInstanceError):
        result.applied = False  # type: ignore[misc]

    updated = result.with_updates(applied=False)
    assert updated.applied is False
    assert result.applied is True


def test_bind_without_registry_records_bound_result() -> None:
    binder = InMemoryPolicyExecutionBinder()
    result = binder.bind(_request())

    assert result.status == "BOUND"
    assert result.applied is True
    assert result.policy_id == "policy-1"
    assert result.policy_version == "1.0.0"
    assert result.metadata["observation_only"] is True


def test_bind_with_registry_records_bound_for_active_policy() -> None:
    registry = InMemoryGovernancePolicyRegistry()
    registry.register(_active_policy())
    binder = InMemoryPolicyExecutionBinder(policy_registry=registry)

    result = binder.bind(_request())

    assert result.status == "BOUND"
    assert result.applied is True


def test_bind_returns_not_found_when_policy_missing() -> None:
    registry = InMemoryGovernancePolicyRegistry()
    binder = InMemoryPolicyExecutionBinder(policy_registry=registry)

    result = binder.bind(_request())

    assert result.status == "NOT_FOUND"
    assert result.applied is False


def test_bind_returns_disabled_when_policy_version_is_disabled() -> None:
    registry = InMemoryGovernancePolicyRegistry()
    registry.register(
        _active_policy().with_updates(status="DISABLED"),
    )
    binder = InMemoryPolicyExecutionBinder(policy_registry=registry)

    result = binder.bind(_request())

    assert result.status == "DISABLED"
    assert result.applied is False
    assert result.metadata["policy_status"] == "DISABLED"


def test_disabled_binder_returns_disabled_status() -> None:
    binder = InMemoryPolicyExecutionBinder(enabled=False)

    result = binder.bind(_request())

    assert result.status == "DISABLED"
    assert result.applied is False
    assert result.metadata["binding_enabled"] is False


def test_get_binding_returns_recorded_result() -> None:
    binder = InMemoryPolicyExecutionBinder()
    bound = binder.bind(_request())

    retrieved = binder.get_binding("exec-policy-bind-1", "policy-1", "1.0.0")

    assert retrieved == bound


def test_get_binding_returns_none_when_missing() -> None:
    binder = InMemoryPolicyExecutionBinder()

    assert binder.get_binding("exec-missing", "policy-1", "1.0.0") is None


def test_list_bindings_filters_by_execution_and_policy() -> None:
    binder = InMemoryPolicyExecutionBinder()
    binder.bind(_request(execution_id="exec-a", policy_id="policy-1"))
    binder.bind(_request(execution_id="exec-b", policy_id="policy-1"))
    binder.bind(_request(execution_id="exec-a", policy_id="policy-2"))

    by_execution = binder.list_bindings(execution_id="exec-a")
    by_policy = binder.list_bindings(policy_id="policy-2")

    assert len(by_execution) == 2
    assert len(by_policy) == 1
    assert by_policy[0].policy_id == "policy-2"


def test_clear_removes_recorded_bindings() -> None:
    binder = InMemoryPolicyExecutionBinder()
    binder.bind(_request())

    binder.clear()

    assert binder.list_bindings() == []
    assert binder.get_binding("exec-policy-bind-1", "policy-1", "1.0.0") is None


def test_metadata_propagates_from_request_and_runtime_context() -> None:
    binder = InMemoryPolicyExecutionBinder()
    result = binder.bind(
        _request(
            runtime_context={"step_id": "step-1"},
            metadata={"correlation_id": "corr-1"},
        )
    )

    assert result.metadata["agent_id"] == "agent-policy-bind-1"
    assert result.metadata["binding_status"] == "BOUND"
    assert result.metadata["runtime_context"] == {"step_id": "step-1"}
    assert result.metadata["correlation_id"] == "corr-1"


def test_binder_is_thread_safe() -> None:
    binder = InMemoryPolicyExecutionBinder()
    errors: list[Exception] = []

    def worker(index: int) -> None:
        try:
            binder.bind(
                _request(
                    execution_id=f"exec-thread-{index}",
                    policy_id=f"policy-{index % 3}",
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


def test_policy_execution_binding_has_no_forbidden_dependencies() -> None:
    for path in _BINDING_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

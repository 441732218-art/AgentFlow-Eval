# AgentFlow Intelligence v2.0 — Governance runtime activation tests (Phase 13.10)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from dataclasses import replace
from pathlib import Path

import pytest

from app.runtime.assembly import (
    PRODUCTION_PROFILE,
    RuntimeAssembler,
    RuntimeAssemblyConfig,
    create_runtime,
)
from app.runtime.governance.activation.memory_activator import (
    InMemoryGovernanceRuntimeActivator,
)
from app.runtime.governance.activation.models import (
    GovernanceActivationRequest,
    GovernanceActivationResult,
)

_ACTIVATION_ROOT = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "runtime"
    / "governance"
    / "activation"
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
    execution_id: str = "exec-activation-1",
    runtime_context: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> GovernanceActivationRequest:
    return GovernanceActivationRequest(
        execution_id=execution_id,
        runtime_context=dict(runtime_context or {"agent_id": "agent-activation-1"}),
        metadata=dict(metadata or {"source": "test"}),
    )


def test_request_creation() -> None:
    request = _request()

    assert request.execution_id == "exec-activation-1"
    assert request.runtime_context["agent_id"] == "agent-activation-1"
    assert request.metadata["source"] == "test"


def test_result_immutable() -> None:
    activator = InMemoryGovernanceRuntimeActivator()
    result = activator.activate(_request())

    with pytest.raises(FrozenInstanceError):
        result.activated = False  # type: ignore[misc]

    updated = result.with_updates(activated=False)
    assert updated.activated is False
    assert result.activated is True


def test_enabled_activation() -> None:
    activator = InMemoryGovernanceRuntimeActivator(enabled=True)
    result = activator.activate(_request())

    assert isinstance(result, GovernanceActivationResult)
    assert result.activated is True
    assert result.governance_enabled is True
    assert result.message == "governance runtime activated"


def test_disabled_activation() -> None:
    activator = InMemoryGovernanceRuntimeActivator(enabled=False)
    result = activator.activate(_request())

    assert result.activated is False
    assert result.governance_enabled is False
    assert result.message == "governance runtime activation disabled"


def test_activation_history() -> None:
    activator = InMemoryGovernanceRuntimeActivator()
    activator.activate(_request(execution_id="exec-activation-1"))
    activator.activate(_request(execution_id="exec-activation-2"))

    history = activator.list_activations()
    assert len(history) == 2
    assert history[0].execution_id == "exec-activation-1"
    assert history[1].execution_id == "exec-activation-2"


def test_get_activation() -> None:
    activator = InMemoryGovernanceRuntimeActivator()
    activator.activate(_request(execution_id="exec-activation-1"))
    activator.activate(_request(execution_id="exec-activation-2"))

    result = activator.get_activation("exec-activation-1")
    assert result is not None
    assert result.execution_id == "exec-activation-1"
    assert activator.get_activation("missing-exec") is None


def test_clear() -> None:
    activator = InMemoryGovernanceRuntimeActivator()
    activator.activate(_request(execution_id="exec-activation-1"))
    activator.clear()

    assert activator.list_activations() == []
    assert activator.get_activation("exec-activation-1") is None


def test_thread_safety() -> None:
    activator = InMemoryGovernanceRuntimeActivator()
    errors: list[Exception] = []

    def worker(index: int) -> None:
        try:
            result = activator.activate(
                _request(execution_id=f"exec-activation-{index}")
            )
            assert result.activated is True
            assert activator.get_activation(result.execution_id) is not None
        except Exception as exc:  # pragma: no cover - surfaced by assertion below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(24)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(activator.list_activations()) == 24


def test_assembly_optional_wiring() -> None:
    profile = replace(PRODUCTION_PROFILE, enable_governance_activation=False)
    assembly = RuntimeAssembler().assemble(RuntimeAssemblyConfig(profile=profile))

    assert assembly.governance_runtime_activator is None


def test_development_profile_enabled() -> None:
    assembly = create_runtime("development")

    assert assembly.profile.enable_governance_activation is True
    assert assembly.governance_runtime_activator is not None
    assert isinstance(
        assembly.governance_runtime_activator,
        InMemoryGovernanceRuntimeActivator,
    )


def test_production_profile_enabled() -> None:
    assembly = create_runtime("production")

    assert assembly.profile.enable_governance_activation is True
    assert assembly.governance_runtime_activator is not None


def test_testing_profile_disabled() -> None:
    assembly = create_runtime("testing")

    assert assembly.profile.enable_governance_activation is False
    assert assembly.governance_runtime_activator is None


def test_governance_activation_has_no_forbidden_dependencies() -> None:
    for path in _ACTIVATION_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

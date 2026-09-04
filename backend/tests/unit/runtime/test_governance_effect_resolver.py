# AgentFlow Intelligence v2.0 — Governance effect resolver tests (Phase 13.2)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.runtime.governance.execution.models import GovernanceExecutionEffect
from app.runtime.governance.resolver.memory_resolver import InMemoryGovernanceEffectResolver
from app.runtime.governance.resolver.models import GovernanceEffectResolution

_RESOLVER_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "resolver"
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


def _effect(*, action_type: str = "ALLOW", effect_id: str = "effect-1") -> GovernanceExecutionEffect:
    return GovernanceExecutionEffect(
        effect_id=effect_id,
        decision_id="decision-1",
        action_type=action_type,  # type: ignore[arg-type]
        target="execution:exec-1",
        reason="governance effect",
        evidence_reference="evidence-1",
        metadata={"source": "test"},
    )


def test_governance_effect_resolution_model_creation() -> None:
    resolution = GovernanceEffectResolution(
        resolution_id="resolution-1",
        effect_id="effect-1",
        resolution_type="CONTINUE",
        executable=True,
        reason="allow",
    )

    assert resolution.resolution_id == "resolution-1"
    assert resolution.resolution_type == "CONTINUE"
    assert resolution.executable is True


def test_governance_effect_resolution_is_immutable() -> None:
    resolution = GovernanceEffectResolution(
        resolution_id="resolution-1",
        effect_id="effect-1",
        resolution_type="CONTINUE",
        executable=True,
        reason="allow",
    )

    with pytest.raises(FrozenInstanceError):
        resolution.executable = False  # type: ignore[misc]

    updated = resolution.with_updates(executable=False)
    assert updated.executable is False
    assert resolution.executable is True


def test_allow_effect_resolves_to_continue() -> None:
    resolver = InMemoryGovernanceEffectResolver()
    resolution = resolver.resolve(_effect(action_type="ALLOW"))

    assert resolution.resolution_type == "CONTINUE"
    assert resolution.executable is True
    assert resolution.reason == "governance effect"


def test_warn_effect_resolves_to_continue_with_warning() -> None:
    resolver = InMemoryGovernanceEffectResolver()
    resolution = resolver.resolve(_effect(action_type="WARN"))

    assert resolution.resolution_type == "CONTINUE_WITH_WARNING"
    assert resolution.executable is True


def test_block_effect_resolves_to_block_request() -> None:
    resolver = InMemoryGovernanceEffectResolver()
    resolution = resolver.resolve(_effect(action_type="BLOCK"))

    assert resolution.resolution_type == "BLOCK_REQUEST"
    assert resolution.executable is False


def test_require_approval_effect_resolves_to_wait_approval() -> None:
    resolver = InMemoryGovernanceEffectResolver()
    resolution = resolver.resolve(_effect(action_type="REQUIRE_APPROVAL"))

    assert resolution.resolution_type == "WAIT_APPROVAL"
    assert resolution.executable is False


def test_get_list_and_clear_resolutions() -> None:
    resolver = InMemoryGovernanceEffectResolver()
    first = resolver.resolve(_effect(effect_id="effect-a"))
    second = resolver.resolve(_effect(effect_id="effect-b", action_type="WARN"))

    assert resolver.get_resolution(first.resolution_id) == first
    assert len(resolver.list_resolutions()) == 2
    assert {resolution.effect_id for resolution in resolver.list_resolutions()} == {
        "effect-a",
        "effect-b",
    }

    resolver.clear()

    assert resolver.list_resolutions() == []
    assert resolver.get_resolution(first.resolution_id) is None


def test_disabled_mode_returns_continue_without_blocking() -> None:
    resolver = InMemoryGovernanceEffectResolver(enabled=False)
    resolution = resolver.resolve(_effect(action_type="BLOCK"))

    assert resolution.resolution_type == "CONTINUE"
    assert resolution.executable is True
    assert resolution.reason == "governance effect resolver disabled"
    assert resolution.metadata["resolver_enabled"] is False


def test_unsupported_action_type_raises() -> None:
    resolver = InMemoryGovernanceEffectResolver()
    effect = _effect().with_updates(action_type="UNKNOWN")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Unsupported governance execution action type"):
        resolver.resolve(effect)


def test_resolver_is_thread_safe() -> None:
    resolver = InMemoryGovernanceEffectResolver()
    errors: list[Exception] = []
    action_types = ("ALLOW", "WARN", "BLOCK", "REQUIRE_APPROVAL")

    def worker(index: int) -> None:
        try:
            resolver.resolve(
                _effect(
                    effect_id=f"effect-thread-{index}",
                    action_type=action_types[index % len(action_types)],
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
    assert len(resolver.list_resolutions()) == 24


def test_governance_effect_resolver_has_no_forbidden_dependencies() -> None:
    for path in _RESOLVER_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

# AgentFlow Intelligence v2.0 — Governance configuration tests (Phase 13.1)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.runtime.governance.configuration.memory_registry import (
    InMemoryGovernanceConfigurationRegistry,
)
from app.runtime.governance.configuration.models import (
    GovernanceConfiguration,
    GovernanceConfigurationScope,
)

_CONFIGURATION_ROOT = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "runtime"
    / "governance"
    / "configuration"
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


def _scope(**overrides: object) -> GovernanceConfigurationScope:
    values = {
        "scope_id": "scope-config-1",
        "agent_id": "agent-config-1",
        "tenant_id": "tenant-config-1",
        "tags": ("governance", "runtime"),
    }
    values.update(overrides)
    return GovernanceConfigurationScope(**values)  # type: ignore[arg-type]


def _configuration(**overrides: object) -> GovernanceConfiguration:
    values = {
        "configuration_id": "config-1",
        "name": "Production Governance",
        "description": "Production governance configuration",
        "enabled": True,
        "environment": "production",
        "metadata": {"owner": "platform"},
        "scope": _scope(),
    }
    values.update(overrides)
    return GovernanceConfiguration(**values)  # type: ignore[arg-type]


def test_governance_configuration_is_immutable() -> None:
    configuration = _configuration()

    with pytest.raises(FrozenInstanceError):
        configuration.enabled = False  # type: ignore[misc]

    updated = configuration.with_updates(enabled=False)
    assert updated.enabled is False
    assert configuration.enabled is True


def test_governance_configuration_scope_is_immutable() -> None:
    scope = _scope()

    with pytest.raises(FrozenInstanceError):
        scope.agent_id = "other-agent"  # type: ignore[misc]

    updated = scope.with_updates(agent_id="other-agent")
    assert updated.agent_id == "other-agent"
    assert scope.agent_id == "agent-config-1"


def test_register_and_get_configuration() -> None:
    registry = InMemoryGovernanceConfigurationRegistry()
    configuration = _configuration()
    registry.register(configuration)

    retrieved = registry.get("config-1")

    assert retrieved == configuration


def test_get_returns_none_for_missing_configuration() -> None:
    registry = InMemoryGovernanceConfigurationRegistry()

    assert registry.get("missing-config") is None


def test_register_replaces_existing_configuration() -> None:
    registry = InMemoryGovernanceConfigurationRegistry()
    registry.register(_configuration())
    updated = _configuration(name="Updated Governance", enabled=False)
    registry.register(updated)

    retrieved = registry.get("config-1")

    assert retrieved == updated
    assert retrieved is not None
    assert retrieved.name == "Updated Governance"
    assert retrieved.enabled is False


def test_list_all_returns_sorted_configurations() -> None:
    registry = InMemoryGovernanceConfigurationRegistry()
    registry.register(_configuration(configuration_id="config-b"))
    registry.register(_configuration(configuration_id="config-a", name="Config A"))

    records = registry.list_all()

    assert [record.configuration_id for record in records] == ["config-a", "config-b"]


def test_list_all_returns_empty_when_registry_is_empty() -> None:
    registry = InMemoryGovernanceConfigurationRegistry()

    assert registry.list_all() == []


def test_remove_configuration() -> None:
    registry = InMemoryGovernanceConfigurationRegistry()
    registry.register(_configuration())

    registry.remove("config-1")

    assert registry.get("config-1") is None
    assert registry.list_all() == []


def test_remove_missing_configuration_is_noop() -> None:
    registry = InMemoryGovernanceConfigurationRegistry()
    registry.register(_configuration())

    registry.remove("missing-config")

    assert registry.get("config-1") is not None


def test_clear_removes_all_configurations() -> None:
    registry = InMemoryGovernanceConfigurationRegistry()
    registry.register(_configuration(configuration_id="config-a"))
    registry.register(_configuration(configuration_id="config-b", name="Config B"))

    registry.clear()

    assert registry.list_all() == []


def test_configuration_preserves_scope_and_metadata() -> None:
    registry = InMemoryGovernanceConfigurationRegistry()
    configuration = _configuration(
        metadata={"owner": "platform", "tier": "enterprise"},
        scope=_scope(tags=("governance", "enterprise")),
    )
    registry.register(configuration)

    retrieved = registry.get("config-1")

    assert retrieved is not None
    assert retrieved.metadata["tier"] == "enterprise"
    assert retrieved.scope is not None
    assert retrieved.scope.tenant_id == "tenant-config-1"
    assert retrieved.scope.tags == ("governance", "enterprise")


def test_configuration_without_scope() -> None:
    registry = InMemoryGovernanceConfigurationRegistry()
    configuration = _configuration(scope=None)
    registry.register(configuration)

    retrieved = registry.get("config-1")

    assert retrieved is not None
    assert retrieved.scope is None


def test_disabled_configuration_is_stored() -> None:
    registry = InMemoryGovernanceConfigurationRegistry()
    registry.register(_configuration(enabled=False, environment="testing"))

    retrieved = registry.get("config-1")

    assert retrieved is not None
    assert retrieved.enabled is False
    assert retrieved.environment == "testing"


def test_registry_is_thread_safe() -> None:
    registry = InMemoryGovernanceConfigurationRegistry()
    errors: list[Exception] = []

    def worker(index: int) -> None:
        try:
            registry.register(
                _configuration(
                    configuration_id=f"config-thread-{index}",
                    name=f"Config {index}",
                )
            )
            registry.get(f"config-thread-{index}")
        except Exception as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(24)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(registry.list_all()) == 24


def test_governance_configuration_has_no_forbidden_dependencies() -> None:
    for path in _CONFIGURATION_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

# AgentFlow Intelligence v2.0 — Agent registry tests (Phase 10.2)

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.agent.runtime import AgentRuntime
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.registry import AgentNotFoundError, InMemoryAgentRegistry

_REGISTRY_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "registry"
_FORBIDDEN_STRINGS = ("app.applications", "trade", "CRM", "Email")


def _agent(agent_id: str = "agent-001", name: str = "probe-agent") -> AgentDefinition:
    return AgentDefinition(
        id=agent_id,
        name=name,
        tool_names=["probe.echo"],
    )


def test_agent_definition_defaults() -> None:
    definition = _agent()

    assert definition.version == "1.0"
    assert definition.enabled is True
    assert definition.metadata == {}


def test_register_agent() -> None:
    registry = InMemoryAgentRegistry()
    definition = _agent()

    registry.register(definition)

    assert registry.get("agent-001") == definition


def test_get_agent() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(_agent())

    assert registry.get("agent-001") is not None
    assert registry.get("missing") is None


def test_list_agents() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(_agent("agent-a", "Agent A"))
    registry.register(_agent("agent-b", "Agent B"))

    agents = registry.list()

    assert len(agents) == 2
    assert {agent.id for agent in agents} == {"agent-a", "agent-b"}


def test_remove_agent() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(_agent())

    registry.remove("agent-001")

    assert registry.get("agent-001") is None


def test_duplicate_register_replaces_existing_agent() -> None:
    registry = InMemoryAgentRegistry()
    registry.register(_agent(name="Original"))
    registry.register(_agent(name="Replacement"))

    stored = registry.get("agent-001")

    assert stored is not None
    assert stored.name == "Replacement"
    assert len(registry.list()) == 1


def test_agent_runtime_lookup_by_agent_id() -> None:
    production_runtime = create_production_runtime()
    registry = InMemoryAgentRegistry()
    registry.register(_agent())
    agent_runtime = AgentRuntime(production_runtime, agent_registry=registry)
    execution_context = create_execution_context(
        production_runtime,
        execution_id="exec-registry-1",
        agent_id="agent-001",
    )

    result = agent_runtime.execute("agent-001", "registry probe", context=execution_context)

    assert result.session.agent_id == "agent-001"
    assert result.session.status == "COMPLETED"


def test_agent_runtime_lookup_missing_agent_raises() -> None:
    production_runtime = create_production_runtime()
    agent_runtime = AgentRuntime(production_runtime, agent_registry=InMemoryAgentRegistry())

    with pytest.raises(AgentNotFoundError, match="missing-agent"):
        agent_runtime.execute("missing-agent", "task")


def test_agent_registry_has_no_applications_dependency() -> None:
    for path in _REGISTRY_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in source, f"{forbidden!r} found in {path}"

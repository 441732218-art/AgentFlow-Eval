# AgentFlow Intelligence v2.0 — in-memory registry tests

from __future__ import annotations

import pytest

from app.core.runtime.agent import Agent
from app.core.runtime.exceptions import AgentNotFoundError, DuplicateAgentError
from app.core.runtime.registry import AgentRegistry, get_agent_registry, reset_agent_registry


def _agent(agent_id: str = "ag-1", name: str = "demo") -> Agent:
    return Agent(agent_id=agent_id, name=name, runner_type="openai", config={})


def test_register_and_get() -> None:
    reg = AgentRegistry()
    agent = _agent()
    stored = reg.register(agent)
    assert stored is agent
    assert reg.get("ag-1") is agent


def test_list_insertion_order() -> None:
    reg = AgentRegistry()
    reg.register(_agent("a", "one"))
    reg.register(_agent("b", "two"))
    ids = [x.agent_id for x in reg.list()]
    assert ids == ["a", "b"]


def test_duplicate_agent_id_rejected() -> None:
    reg = AgentRegistry()
    reg.register(_agent("dup"))
    with pytest.raises(DuplicateAgentError) as exc:
        reg.register(_agent("dup", "other"))
    assert exc.value.agent_id == "dup"


def test_missing_agent_raises() -> None:
    reg = AgentRegistry()
    with pytest.raises(AgentNotFoundError) as exc:
        reg.get("missing")
    assert exc.value.agent_id == "missing"


def test_register_rejects_empty_agent_id() -> None:
    reg = AgentRegistry()
    with pytest.raises(ValueError, match="agent_id"):
        reg.register(Agent(agent_id="  ", name="n", runner_type="openai"))


def test_register_rejects_non_agent() -> None:
    reg = AgentRegistry()
    with pytest.raises(TypeError):
        reg.register({"agent_id": "x"})  # type: ignore[arg-type]


def test_reset_singleton_isolates_tests() -> None:
    reset_agent_registry()
    first = get_agent_registry()
    first.register(_agent("iso"))
    second = reset_agent_registry()
    assert second is get_agent_registry()
    with pytest.raises(AgentNotFoundError):
        second.get("iso")

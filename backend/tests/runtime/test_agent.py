# AgentFlow Intelligence v2.0 — Agent entity tests

from __future__ import annotations

from dataclasses import asdict, fields

from app.core.runtime.agent import Agent


def test_agent_create_minimal_fields() -> None:
    agent = Agent(
        agent_id="ag-1",
        name="demo",
        runner_type="openai",
    )
    assert agent.agent_id == "ag-1"
    assert agent.name == "demo"
    assert agent.runner_type == "openai"
    assert agent.config == {}


def test_agent_create_with_config() -> None:
    cfg = {"model": "gpt-4o-mini", "max_iterations": 3}
    agent = Agent(
        agent_id="ag-2",
        name="http-bot",
        runner_type="http",
        config=cfg,
    )
    assert agent.config["model"] == "gpt-4o-mini"
    assert agent.config is cfg


def test_agent_only_allowed_fields() -> None:
    names = {f.name for f in fields(Agent)}
    assert names == {"agent_id", "name", "runner_type", "config"}


def test_agent_config_default_is_independent() -> None:
    a = Agent(agent_id="a", name="n", runner_type="openai")
    b = Agent(agent_id="b", name="n", runner_type="openai")
    a.config["k"] = 1
    assert "k" not in b.config


def test_agent_asdict_roundtrip() -> None:
    agent = Agent(agent_id="x", name="y", runner_type="echo", config={"runner": "echo"})
    data = asdict(agent)
    assert data["agent_id"] == "x"
    assert data["runner_type"] == "echo"
    clone = Agent(**data)
    assert clone == agent

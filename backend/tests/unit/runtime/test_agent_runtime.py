# AgentFlow Intelligence v2.0 — Agent runtime service layer tests (Phase 10.1)

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.runtime.agent.lifecycle import complete_session, fail_session, start_session
from app.runtime.agent.models import AgentDefinition
from app.runtime.agent.runtime import AgentRuntime
from app.runtime.agent.session import ExecutionSession
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.events.event_types import RuntimeEventType
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.observability.events import RuntimeEventType as ObservationEventType

_AGENT_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "agent"
_FORBIDDEN_STRINGS = ("applications", "trade", "CRM", "Email")


def _agent_definition() -> AgentDefinition:
    return AgentDefinition(
        id="agent-001",
        name="probe-agent",
        tool_names=["probe.echo"],
        metadata={"version": "1"},
    )


def _runtime_stack() -> tuple:
    production_runtime = create_production_runtime()
    execution_context = create_execution_context(
        production_runtime,
        execution_id="exec-agent-1",
        agent_id="agent-001",
        tenant_id="tenant-1",
    )
    agent_runtime = AgentRuntime(production_runtime)
    return production_runtime, execution_context, agent_runtime


def test_agent_definition_creation() -> None:
    definition = _agent_definition()

    assert definition.id == "agent-001"
    assert definition.name == "probe-agent"
    assert definition.tool_names == ["probe.echo"]
    assert definition.metadata["version"] == "1"


def test_execution_session_lifecycle_helpers() -> None:
    production_runtime, execution_context, _ = _runtime_stack()
    definition = _agent_definition()

    session = start_session(
        definition,
        execution_context,
        task="run probe",
        execution_id="exec-session-1",
    )
    assert session.status == "RUNNING"
    assert session.started_at is not None

    complete_session(
        session,
        execution_context,
        agent_definition=definition,
        output={"ok": True},
    )
    assert session.status == "COMPLETED"
    assert session.finished_at is not None

    failed_session = ExecutionSession(
        execution_id="exec-session-2",
        agent_id=definition.id,
        status="RUNNING",
        started_at=session.started_at,
    )
    fail_session(
        failed_session,
        execution_context,
        agent_definition=definition,
        error=RuntimeError("probe failed"),
    )
    assert failed_session.status == "FAILED"
    assert failed_session.finished_at is not None


def test_agent_started_event_emitted() -> None:
    production_runtime, execution_context, agent_runtime = _runtime_stack()
    definition = _agent_definition()

    agent_runtime.execute(definition, "start probe", context=execution_context)

    published = production_runtime.event_publisher.get_events()
    assert any(event.event_type == RuntimeEventType.AGENT_STARTED for event in published)


def test_agent_completed_event_emitted() -> None:
    production_runtime, execution_context, agent_runtime = _runtime_stack()
    definition = _agent_definition()

    result = agent_runtime.execute(definition, "complete probe", context=execution_context)

    assert result.session.status == "COMPLETED"
    published = production_runtime.event_publisher.get_events()
    assert any(event.event_type == RuntimeEventType.AGENT_COMPLETED for event in published)


def test_agent_failed_event_emitted() -> None:
    production_runtime, execution_context, agent_runtime = _runtime_stack()
    definition = _agent_definition()

    with patch.object(agent_runtime._pipeline, "run", side_effect=RuntimeError("pipeline failed")):
        result = agent_runtime.execute(definition, "fail probe", context=execution_context)

    assert result.session.status == "FAILED"
    assert result.error == "pipeline failed"
    published = production_runtime.event_publisher.get_events()
    assert any(event.event_type == RuntimeEventType.AGENT_FAILED for event in published)


def test_context_governance_wiring_preserved() -> None:
    production_runtime, execution_context, agent_runtime = _runtime_stack()

    assert execution_context.observation_collector is production_runtime.observation_collector
    assert execution_context.event_publisher is production_runtime.event_publisher
    assert execution_context.audit_store is production_runtime.audit_store
    assert execution_context.policy_engine is production_runtime.policy_engine
    assert execution_context.governance_lifecycle is production_runtime.governance_lifecycle

    agent_runtime.execute(_agent_definition(), "governance probe", context=execution_context)

    observations = production_runtime.observation_collector.get_events()
    assert any(event.event_type == ObservationEventType.AGENT_STARTED for event in observations)


def test_agent_runtime_has_no_applications_dependency() -> None:
    for path in _AGENT_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "app.applications" not in source
        for forbidden in _FORBIDDEN_STRINGS:
            if forbidden == "applications":
                continue
            assert forbidden not in source, f"{forbidden!r} found in {path}"

# AgentFlow Intelligence v2.0 — Runtime bootstrap tests (Phase 10.0)

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.bootstrap.config import RuntimeConfig
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.context import RuntimeContext
from app.runtime.events.event_types import RuntimeEventType
from app.runtime.executor.context_fields import attach_execution_context, attach_tool_request
from app.runtime.observability.events import RuntimeEventType as ObservationEventType
from app.runtime.pipeline.tool_step import execute_tool_via_engine
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.local_adapter import LocalToolExecutorAdapter

_BOOTSTRAP_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "bootstrap"
_FORBIDDEN_STRINGS = ("trade", "CRM", "Email")


def test_create_production_runtime_success() -> None:
    runtime = create_production_runtime()

    assert runtime.config.environment == "production"
    assert runtime.policy_engine is not None
    assert runtime.observation_collector is not None
    assert runtime.event_publisher is not None
    assert runtime.audit_store is not None
    assert runtime.governance_lifecycle is not None
    assert runtime.tool_execution_engine is not None


def test_create_execution_context_injects_all_components() -> None:
    runtime = create_production_runtime()
    execution_context = create_execution_context(
        runtime,
        execution_id="exec-bootstrap-1",
        agent_id="agent-1",
        tenant_id="tenant-1",
        user_id="user-1",
    )

    assert execution_context.execution_id == "exec-bootstrap-1"
    assert execution_context.observation_collector is runtime.observation_collector
    assert execution_context.event_publisher is runtime.event_publisher
    assert execution_context.audit_store is runtime.audit_store
    assert execution_context.policy_engine is runtime.policy_engine
    assert execution_context.governance_lifecycle is runtime.governance_lifecycle


def test_governance_flow_via_bootstrap() -> None:
    runtime = create_production_runtime()
    adapter = runtime.tool_execution_engine.adapter_registry.get("local")
    assert isinstance(adapter, LocalToolExecutorAdapter)
    adapter.handler_registry.register("probe.echo", lambda message: {"echo": message})

    execution_context = create_execution_context(
        runtime,
        execution_id="exec-bootstrap-2",
        agent_id="agent-2",
        tenant_id="tenant-2",
    )
    definition = ToolDefinition(
        name="probe.echo",
        description="Bootstrap probe",
        executor_type="local",
        input_schema={"type": "object"},
    )
    pipeline_context = attach_tool_request(
        RuntimeContext(execution_id="exec-bootstrap-2", agent_id="agent-2"),
        definition,
        {"message": "hello"},
    )
    attach_execution_context(pipeline_context, execution_context)

    output = execute_tool_via_engine(pipeline_context, runtime.tool_execution_engine)

    assert output == {"echo": "hello"}

    observations = runtime.observation_collector.get_events()
    observation_types = [event.event_type for event in observations]
    assert ObservationEventType.TOOL_STARTED in observation_types
    assert ObservationEventType.TOOL_COMPLETED in observation_types

    published = runtime.event_publisher.get_events()
    published_types = [event.event_type for event in published]
    assert RuntimeEventType.TOOL_STARTED in published_types
    assert RuntimeEventType.TOOL_COMPLETED in published_types

    audit_records = runtime.audit_store.query(execution_id="exec-bootstrap-2")
    assert len(audit_records) >= 2


def test_disable_governance_keeps_backward_compatible_execution() -> None:
    config = RuntimeConfig(enable_governance=False)
    runtime = create_production_runtime(config)
    adapter = runtime.tool_execution_engine.adapter_registry.get("local")
    assert isinstance(adapter, LocalToolExecutorAdapter)
    adapter.handler_registry.register("legacy.echo", lambda message: message)

    execution_context = create_execution_context(
        runtime,
        execution_id="exec-bootstrap-legacy",
        agent_id="agent-legacy",
    )

    assert execution_context.governance_lifecycle is None
    assert execution_context.policy_engine is None

    definition = ToolDefinition(
        name="legacy.echo",
        description="Legacy probe",
        executor_type="local",
        input_schema={"type": "object"},
    )
    pipeline_context = attach_tool_request(
        RuntimeContext(execution_id="exec-bootstrap-legacy", agent_id="agent-legacy"),
        definition,
        {"message": "legacy"},
    )
    attach_execution_context(pipeline_context, execution_context)

    output = execute_tool_via_engine(pipeline_context, runtime.tool_execution_engine)

    assert output == "legacy"


def test_execution_context_remote_payload_security() -> None:
    runtime = create_production_runtime()
    execution_context = create_execution_context(
        runtime,
        execution_id="exec-bootstrap-payload",
        agent_id="agent-payload",
        tenant_id="tenant-payload",
    )

    payload = execution_context.to_remote_payload()

    assert payload == {
        "execution_id": "exec-bootstrap-payload",
        "agent_id": "agent-payload",
        "tenant_id": "tenant-payload",
    }
    for forbidden in (
        "event_publisher",
        "observation_collector",
        "audit_store",
        "policy_engine",
        "governance_lifecycle",
    ):
        assert forbidden not in payload


def test_runtime_config_rejects_invalid_environment() -> None:
    with pytest.raises(ValueError, match="environment"):
        RuntimeConfig(environment="invalid")


def test_runtime_bootstrap_has_no_business_leakage() -> None:
    for path in _BOOTSTRAP_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in source, f"{forbidden!r} found in {path}"

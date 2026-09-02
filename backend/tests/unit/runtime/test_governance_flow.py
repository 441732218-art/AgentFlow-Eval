# AgentFlow Intelligence v2.0 — Runtime governance flow tests (Phase 9.9)

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.runtime.audit.memory_store import InMemoryAuditStore
from app.runtime.context import RuntimeContext
from app.runtime.events.event_types import RuntimeEventType
from app.runtime.events.publisher import InMemoryEventPublisher
from app.runtime.executor.context_fields import attach_execution_context, attach_tool_request
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.governance.lifecycle import RuntimeGovernanceLifecycle
from app.runtime.observability.collector import InMemoryObservationCollector
from app.runtime.observability.events import RuntimeEventType as ObservationEventType
from app.runtime.pipeline.tool_step import execute_tool_via_engine
from app.runtime.policy.engine import InMemoryPolicyEngine
from app.runtime.policy.models import PolicyDeniedError
from app.runtime.tools.adapter import ToolExecutorAdapter
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.engine import ToolExecutionEngine
from app.runtime.tools.executor_registry import ToolExecutorRegistry

_GOVERNANCE_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance"
_RUNTIME_SCAN_PATHS = (
    _GOVERNANCE_ROOT,
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "executor",
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "tools",
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "events",
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "observability",
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "audit",
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "policy",
)
_FORBIDDEN_STRINGS = ("trade_provider", "trade.", "CRM", "Email")


def _governed_context(
    *,
    execution_id: str = "exec-gov-1",
    blocked_tools: list[str] | None = None,
) -> ExecutionContext:
    lifecycle = RuntimeGovernanceLifecycle()
    collector = InMemoryObservationCollector()
    audit_store = InMemoryAuditStore()
    publisher = InMemoryEventPublisher(audit_store=audit_store)
    return ExecutionContext(
        execution_id=execution_id,
        agent_id="agent-gov",
        tenant_id="tenant-gov",
        observation_collector=collector,
        event_publisher=publisher,
        audit_store=audit_store,
        policy_engine=InMemoryPolicyEngine(blocked_tools=blocked_tools or []),
        governance_lifecycle=lifecycle,
    )


class LocalProbeAdapter(ToolExecutorAdapter):
    executor_type = "local"

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[str] = []
        self._fail = fail

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
        *,
        execution_context: ExecutionContext | None = None,
    ) -> Any:
        _ = arguments, execution_context
        self.calls.append(tool_definition.name)
        if self._fail:
            raise ValueError("tool failed")
        return {"ok": True, "tool": tool_definition.name}


def _definition(name: str = "safe.tool") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Governance test tool",
        executor_type="local",
        input_schema={"type": "object"},
    )


def test_full_success_governance_flow() -> None:
    execution_context = _governed_context()
    adapter = LocalProbeAdapter()
    registry = ToolExecutorRegistry()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)
    runtime = attach_tool_request(
        RuntimeContext(execution_id=execution_context.execution_id, agent_id="agent-gov"),
        _definition(),
        {"query": "x"},
    )
    attach_execution_context(runtime, execution_context)

    output = execute_tool_via_engine(runtime, engine)

    assert output == {"ok": True, "tool": "safe.tool"}
    assert adapter.calls == ["safe.tool"]

    observations = execution_context.observation_collector.get_events()
    observation_types = [event.event_type for event in observations]
    assert ObservationEventType.TOOL_STARTED in observation_types
    assert ObservationEventType.TOOL_COMPLETED in observation_types

    published = execution_context.event_publisher.get_events()
    published_types = [event.event_type for event in published]
    assert RuntimeEventType.TOOL_STARTED in published_types
    assert RuntimeEventType.TOOL_COMPLETED in published_types

    audit_records = execution_context.audit_store.query(
        execution_id=execution_context.execution_id
    )
    assert len(audit_records) >= 2
    assert any(record.event_type == ObservationEventType.TOOL_COMPLETED for record in audit_records)


def test_policy_deny_governance_flow() -> None:
    execution_context = _governed_context(
        execution_id="exec-gov-deny",
        blocked_tools=["dangerous.tool"],
    )
    adapter = LocalProbeAdapter()
    registry = ToolExecutorRegistry()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)
    runtime = attach_tool_request(
        RuntimeContext(execution_id=execution_context.execution_id, agent_id="agent-gov"),
        _definition("dangerous.tool"),
        {},
    )
    attach_execution_context(runtime, execution_context)

    with pytest.raises(PolicyDeniedError):
        execute_tool_via_engine(runtime, engine)

    assert adapter.calls == []

    published = execution_context.event_publisher.get_events()
    assert any(event.event_type == RuntimeEventType.TOOL_POLICY_DENIED for event in published)

    audit_records = execution_context.audit_store.query(
        execution_id=execution_context.execution_id
    )
    assert any(record.event_type == ObservationEventType.TOOL_POLICY_DENIED for record in audit_records)


def test_tool_exception_governance_flow() -> None:
    execution_context = _governed_context(execution_id="exec-gov-fail")
    adapter = LocalProbeAdapter(fail=True)
    registry = ToolExecutorRegistry()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)
    runtime = attach_tool_request(
        RuntimeContext(execution_id=execution_context.execution_id, agent_id="agent-gov"),
        _definition("failing.tool"),
        {},
    )
    attach_execution_context(runtime, execution_context)

    with pytest.raises(ValueError, match="tool failed"):
        execute_tool_via_engine(runtime, engine)

    observations = execution_context.observation_collector.get_events()
    assert any(event.event_type == ObservationEventType.TOOL_FAILED for event in observations)

    audit_records = execution_context.audit_store.query(
        execution_id=execution_context.execution_id
    )
    assert any(record.event_type == ObservationEventType.TOOL_FAILED for record in audit_records)


def test_without_governance_lifecycle_keeps_legacy_behavior() -> None:
    collector = InMemoryObservationCollector()
    execution_context = ExecutionContext(
        execution_id="exec-legacy",
        agent_id="agent-legacy",
        observation_collector=collector,
    )
    adapter = LocalProbeAdapter()
    registry = ToolExecutorRegistry()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)
    runtime = attach_tool_request(
        RuntimeContext(execution_id="exec-legacy", agent_id="agent-legacy"),
        _definition(),
        {},
    )
    attach_execution_context(runtime, execution_context)

    output = execute_tool_via_engine(runtime, engine)

    assert output == {"ok": True, "tool": "safe.tool"}
    observations = collector.get_events()
    assert any(event.event_type == ObservationEventType.TOOL_STARTED for event in observations)
    assert any(event.event_type == ObservationEventType.TOOL_COMPLETED for event in observations)


def test_remote_payload_does_not_leak_governance_internals() -> None:
    execution_context = _governed_context(execution_id="exec-gov-payload")

    payload = execution_context.to_remote_payload()

    assert payload == {
        "execution_id": "exec-gov-payload",
        "agent_id": "agent-gov",
        "tenant_id": "tenant-gov",
    }
    for forbidden in (
        "event_publisher",
        "observation_collector",
        "audit_store",
        "policy_engine",
        "governance_lifecycle",
    ):
        assert forbidden not in payload


def test_runtime_governance_has_no_business_leakage() -> None:
    for root in _RUNTIME_SCAN_PATHS:
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for forbidden in _FORBIDDEN_STRINGS:
                assert forbidden not in source, f"{forbidden!r} found in {path}"

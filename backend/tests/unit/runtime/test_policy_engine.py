# AgentFlow Intelligence v2.0 — Runtime policy engine tests (Phase 9.8)

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.runtime.audit.memory_store import InMemoryAuditStore
from app.runtime.events.event_types import RuntimeEventType
from app.runtime.events.publisher import InMemoryEventPublisher
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.observability.events import RuntimeEventType as ObservationEventType
from app.runtime.policy.engine import InMemoryPolicyEngine, PolicyEngine
from app.runtime.policy.models import PolicyDecision, PolicyDeniedError
from app.runtime.tools.adapter import ToolExecutorAdapter
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.engine import ToolExecutionEngine
from app.runtime.tools.executor_registry import ToolExecutorRegistry

_POLICY_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "policy"
_POLICY_SCAN_PATHS = (
    _POLICY_ROOT,
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "tools" / "engine.py",
)
_FORBIDDEN_STRINGS = ("trade_provider", "CRM", "Email", "database")


def _definition(name: str = "safe.tool") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Policy test tool",
        executor_type="local",
        input_schema={"type": "object"},
    )


class RecordingAdapter(ToolExecutorAdapter):
    executor_type = "local"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
        *,
        execution_context: ExecutionContext | None = None,
    ) -> Any:
        _ = arguments, execution_context
        self.calls.append(tool_definition.name)
        return {"ok": True}


def test_default_allow_when_no_policy_engine() -> None:
    adapter = RecordingAdapter()
    registry = ToolExecutorRegistry()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)
    context = ExecutionContext(execution_id="exec-1", agent_id="agent-1")

    result = engine.execute(_definition(), {}, context=context)

    assert result.output == {"ok": True}
    assert adapter.calls == ["safe.tool"]


def test_blocked_tool_is_denied() -> None:
    adapter = RecordingAdapter()
    registry = ToolExecutorRegistry()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)
    context = ExecutionContext(
        execution_id="exec-2",
        agent_id="agent-2",
        policy_engine=InMemoryPolicyEngine(blocked_tools=["dangerous.tool"]),
    )

    with pytest.raises(PolicyDeniedError, match="dangerous.tool"):
        engine.execute(_definition("dangerous.tool"), {}, context=context)

    assert adapter.calls == []


def test_denied_tool_never_reaches_adapter() -> None:
    adapter = RecordingAdapter()
    registry = ToolExecutorRegistry()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)
    context = ExecutionContext(
        execution_id="exec-3",
        policy_engine=InMemoryPolicyEngine(blocked_tools=["dangerous.tool"]),
    )

    with pytest.raises(PolicyDeniedError):
        engine.execute(_definition("dangerous.tool"), {}, context=context)

    assert adapter.calls == []


class BrokenPolicyEngine:
    def evaluate(
        self,
        context: ExecutionContext | None,
        tool_definition: ToolDefinition,
    ) -> PolicyDecision:
        _ = context, tool_definition
        raise RuntimeError("policy unavailable")


def test_policy_exception_fails_open_and_allows_execution() -> None:
    adapter = RecordingAdapter()
    registry = ToolExecutorRegistry()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)
    context = ExecutionContext(
        execution_id="exec-4",
        policy_engine=BrokenPolicyEngine(),
    )

    result = engine.execute(_definition(), {}, context=context)

    assert result.output == {"ok": True}
    assert adapter.calls == ["safe.tool"]


def test_denied_tool_publishes_policy_event() -> None:
    publisher = InMemoryEventPublisher()
    context = ExecutionContext(
        execution_id="exec-5",
        event_publisher=publisher,
        policy_engine=InMemoryPolicyEngine(blocked_tools=["dangerous.tool"]),
    )
    adapter = RecordingAdapter()
    registry = ToolExecutorRegistry()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)

    with pytest.raises(PolicyDeniedError):
        engine.execute(_definition("dangerous.tool"), {}, context=context)

    published = publisher.get_events()
    assert len(published) == 1
    assert published[0].event_type == RuntimeEventType.TOOL_POLICY_DENIED
    assert published[0].payload["tool_name"] == "dangerous.tool"
    assert published[0].payload["policy_name"] == "in_memory"


def test_denied_tool_persists_audit_record() -> None:
    audit_store = InMemoryAuditStore()
    publisher = InMemoryEventPublisher(audit_store=audit_store)
    context = ExecutionContext(
        execution_id="exec-6",
        tenant_id="tenant-6",
        event_publisher=publisher,
        audit_store=audit_store,
        policy_engine=InMemoryPolicyEngine(blocked_tools=["dangerous.tool"]),
    )
    adapter = RecordingAdapter()
    registry = ToolExecutorRegistry()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)

    with pytest.raises(PolicyDeniedError):
        engine.execute(_definition("dangerous.tool"), {}, context=context)

    records = audit_store.query(execution_id="exec-6", tenant_id="tenant-6")
    assert len(records) == 1
    assert records[0].event_type == ObservationEventType.TOOL_POLICY_DENIED


def test_remote_payload_does_not_leak_policy_engine() -> None:
    context = ExecutionContext(
        execution_id="exec-7",
        agent_id="agent-7",
        tenant_id="tenant-7",
        policy_engine=InMemoryPolicyEngine(blocked_tools=["dangerous.tool"]),
    )

    payload = context.to_remote_payload()

    assert payload == {
        "execution_id": "exec-7",
        "agent_id": "agent-7",
        "tenant_id": "tenant-7",
    }
    assert "policy_engine" not in payload


def test_policy_decision_model_fields() -> None:
    decision = PolicyDecision(
        allowed=False,
        policy_name="in_memory",
        reason="tool blocked",
        metadata={"tool_name": "dangerous.tool"},
    )

    assert decision.allowed is False
    assert decision.policy_name == "in_memory"
    assert decision.reason == "tool blocked"


def test_runtime_policy_code_has_no_business_leakage() -> None:
    paths = list(_POLICY_ROOT.rglob("*.py"))
    paths.append(_POLICY_SCAN_PATHS[1])
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in source, f"{forbidden!r} found in {path}"

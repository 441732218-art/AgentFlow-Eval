# AgentFlow Intelligence v2.0 — Tool invocation guard tests (Phase 10.14)

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.invocation.errors import ToolInvocationDeniedError
from app.runtime.invocation.guard import ToolInvocationGuard
from app.runtime.invocation.models import ToolInvocationContext
from app.runtime.observability.collector import InMemoryObservationCollector
from app.runtime.observability.events import RuntimeEventType
from app.runtime.permissions.evaluator import PermissionEvaluator
from app.runtime.policy.engine import InMemoryPolicyEngine
from app.runtime.tools.adapter import ToolExecutorAdapter
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.engine import ToolExecutionEngine
from app.runtime.tools.executor_registry import ToolExecutorRegistry
from app.runtime.tool_registry.memory_registry import InMemoryToolRegistry
from app.runtime.tool_registry.models import ToolCapability

_INVOCATION_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "invocation"
_FORBIDDEN_STRINGS = (
    "app.applications",
    "app.api",
    "app.service",
    "app.tracing",
    "app.runtime.memory",
    "openai",
    "langgraph",
    "sqlalchemy",
    "postgres",
    "oauth",
    "auth0",
)


class StubAdapter(ToolExecutorAdapter):
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
        return {"tool": tool_definition.name}


def _capability(
    tool_name: str = "email.send",
    *,
    enabled: bool = True,
    permission_scope: tuple[str, ...] = ("email.send",),
) -> ToolCapability:
    return ToolCapability(
        tool_name=tool_name,
        version="1.0",
        description="Send email",
        capability_tags=("communication",),
        permission_scope=permission_scope,
        enabled=enabled,
    )


def _definition(name: str = "email.send") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Send email",
        executor_type="local",
    )


def _invocation(tool_name: str = "email.send") -> ToolInvocationContext:
    return ToolInvocationContext(
        tool_name=tool_name,
        execution_id="exec-invocation-1",
        agent_id="agent-invocation-1",
        metadata={"source": "test"},
    )


def _engine_with_guard(
    *,
    blocked_tools: list[str] | None = None,
    capabilities: list[ToolCapability] | None = None,
) -> tuple[ToolExecutionEngine, StubAdapter, InMemoryObservationCollector]:
    registry = InMemoryToolRegistry()
    for capability in capabilities or [_capability()]:
        registry.register(capability)
    guard = ToolInvocationGuard(
        registry,
        PermissionEvaluator(InMemoryPolicyEngine(blocked_tools=blocked_tools or [])),
    )
    adapter = StubAdapter()
    adapter_registry = ToolExecutorRegistry()
    adapter_registry.register(adapter)
    collector = InMemoryObservationCollector()
    engine = ToolExecutionEngine(
        adapter_registry=adapter_registry,
        invocation_guard=guard,
    )
    return engine, adapter, collector


def test_tool_invocation_context_creation() -> None:
    context = _invocation()

    assert context.tool_name == "email.send"
    assert context.execution_id == "exec-invocation-1"
    assert context.agent_id == "agent-invocation-1"
    assert context.metadata["source"] == "test"


def test_tool_invocation_guard_allows_registered_capability() -> None:
    registry = InMemoryToolRegistry()
    registry.register(_capability())
    guard = ToolInvocationGuard(registry)

    decision = guard.authorize(_invocation(), _definition())

    assert decision.allowed is True


def test_tool_invocation_guard_allows_permitted_tool() -> None:
    registry = InMemoryToolRegistry()
    registry.register(_capability())
    guard = ToolInvocationGuard(
        registry,
        PermissionEvaluator(InMemoryPolicyEngine()),
    )

    decision = guard.authorize(_invocation(), _definition())

    assert decision.allowed is True


def test_tool_invocation_guard_denies_blocked_permission() -> None:
    registry = InMemoryToolRegistry()
    registry.register(_capability())
    guard = ToolInvocationGuard(
        registry,
        PermissionEvaluator(InMemoryPolicyEngine(blocked_tools=["email.send"])),
    )

    decision = guard.authorize(_invocation(), _definition())

    assert decision.allowed is False


def test_tool_invocation_guard_denies_disabled_capability() -> None:
    registry = InMemoryToolRegistry()
    registry.register(_capability(enabled=False))
    guard = ToolInvocationGuard(registry)

    decision = guard.authorize(_invocation(), _definition())

    assert decision.allowed is False
    assert "disabled" in (decision.reason or "").lower()


def test_tool_invocation_guard_denies_missing_capability() -> None:
    guard = ToolInvocationGuard(InMemoryToolRegistry())

    decision = guard.authorize(_invocation("missing.tool"), _definition("missing.tool"))

    assert decision.allowed is False
    assert decision.policy_name == "tool_capability_registry"


def test_tool_execution_engine_integrates_invocation_guard() -> None:
    engine, adapter, collector = _engine_with_guard()
    context = ExecutionContext(
        execution_id="exec-engine-guard",
        agent_id="agent-engine-guard",
        observation_collector=collector,
    )

    result = engine.execute(_definition(), {"to": "user@example.com"}, context=context)

    assert result.output == {"tool": "email.send"}
    assert adapter.calls == ["email.send"]


def test_tool_execution_engine_denies_with_invocation_guard() -> None:
    engine, adapter, collector = _engine_with_guard(blocked_tools=["email.send"])
    context = ExecutionContext(
        execution_id="exec-engine-guard-deny",
        agent_id="agent-engine-guard-deny",
        observation_collector=collector,
    )

    with pytest.raises(ToolInvocationDeniedError, match="email.send"):
        engine.execute(_definition(), {}, context=context)

    assert adapter.calls == []
    events = collector.get_events()
    assert len(events) == 1
    assert events[0].event_type == RuntimeEventType.TOOL_INVOCATION_DENIED


def test_tool_execution_engine_without_guard_preserves_behavior() -> None:
    adapter = StubAdapter()
    adapter_registry = ToolExecutorRegistry()
    adapter_registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=adapter_registry)

    result = engine.execute(_definition(), {"to": "user@example.com"})

    assert result.output == {"tool": "email.send"}
    assert adapter.calls == ["email.send"]


def test_invocation_module_has_no_forbidden_dependencies() -> None:
    for path in _INVOCATION_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

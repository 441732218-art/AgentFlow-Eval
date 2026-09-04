# AgentFlow Intelligence v2.0 — Tool lifecycle governance tests (Phase 12.3)

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.assembly import RuntimeAssembler, RuntimeAssemblyConfig, create_runtime, get_profile
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.evidence.collector import RuntimeEvidenceCollector
from app.runtime.evidence.memory_store import InMemoryEvidenceStore
from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.governance.lifecycle.models import GovernanceLifecycleContext
from app.runtime.governance.tool_hooks.adapter import (
    ToolLifecycleGovernanceAdapter,
    tool_governance_hook_context_from_event,
)
from app.runtime.governance.tool_hooks.models import ToolGovernanceHookContext
from app.runtime.hooks.memory_manager import InMemoryRuntimeHookManager
from app.runtime.hooks.models import (
    TOOL_COMPLETED,
    TOOL_FAILED,
    TOOL_STARTED,
    RuntimeHookEvent,
)
from app.runtime.permissions.evaluator import PermissionEvaluator
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline
from app.runtime.policy.engine import InMemoryPolicyEngine
from app.runtime.policy.models import PolicyDecision
from app.runtime.tool_registry.models import ToolCapability

_ADAPTER_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "tool_hooks"
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
    "ToolExecutionEngine",
    "PolicyEngine",
    "AgentRuntime",
    "ExecutionContext",
)


def _hook_event(event_type: str, *, tool_name: str = "probe.echo") -> RuntimeHookEvent:
    return RuntimeHookEvent(
        event_id="tool-hook-event-1",
        event_type=event_type,  # type: ignore[arg-type]
        execution_id="exec-tool-gov-1",
        agent_id="agent-tool-gov-1",
        timestamp=datetime(2026, 9, 4, 2, 0, tzinfo=timezone.utc),
        payload={
            "tool_name": tool_name,
            "correlation_id": "corr-tool-1",
            "executor_type": "local",
        },
    )


def _agent() -> AgentDefinition:
    return AgentDefinition(
        id="agent-tool-gov-1",
        name="tool-governance-agent",
        tool_names=["probe.echo"],
    )


class RecordingLifecycleManager:
    def __init__(self) -> None:
        self.start_calls: list[GovernanceLifecycleContext] = []
        self.evaluate_calls: list[GovernanceLifecycleContext] = []

    def start(self, context: GovernanceLifecycleContext) -> GovernanceLifecycleContext:
        self.start_calls.append(context)
        return context.with_updates(metadata={**context.metadata, "lifecycle_status": "STARTED"})

    def evaluate(self, context: GovernanceLifecycleContext) -> GovernanceLifecycleContext:
        self.evaluate_calls.append(context)
        return context.with_updates(metadata={**context.metadata, "lifecycle_status": "EVALUATED"})


class FailingLifecycleManager:
    def start(self, context: GovernanceLifecycleContext) -> GovernanceLifecycleContext:
        raise RuntimeError("tool governance start failed")

    def evaluate(self, context: GovernanceLifecycleContext) -> GovernanceLifecycleContext:
        raise RuntimeError("tool governance evaluate failed")


class RecordingPermissionEvaluator:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed
        self.calls: list[tuple[object | None, ToolCapability]] = []

    def evaluate_tool_access(
        self,
        context: object | None,
        tool_capability: ToolCapability,
    ) -> PolicyDecision:
        self.calls.append((context, tool_capability))
        return PolicyDecision(
            allowed=self.allowed,
            policy_name="recording_policy",
            reason=None if self.allowed else "tool access denied for observation",
        )


def test_tool_governance_hook_context_is_immutable() -> None:
    context = ToolGovernanceHookContext(
        execution_id="exec-tool-gov-1",
        agent_id="agent-tool-gov-1",
        tool_name="probe.echo",
        event_type=TOOL_STARTED,
        timestamp=datetime(2026, 9, 4, 2, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(FrozenInstanceError):
        context.tool_name = "other.tool"  # type: ignore[misc]

    updated = context.with_updates(tool_name="other.tool")
    assert updated.tool_name == "other.tool"
    assert context.tool_name == "probe.echo"


def test_tool_governance_hook_context_from_event() -> None:
    context = tool_governance_hook_context_from_event(_hook_event(TOOL_STARTED))

    assert context.execution_id == "exec-tool-gov-1"
    assert context.agent_id == "agent-tool-gov-1"
    assert context.tool_name == "probe.echo"
    assert context.event_type == TOOL_STARTED
    assert context.metadata["executor_type"] == "local"


def test_adapter_receives_tool_started() -> None:
    manager = RecordingLifecycleManager()
    adapter = ToolLifecycleGovernanceAdapter(manager)  # type: ignore[arg-type]

    adapter.before_tool(_hook_event(TOOL_STARTED))

    assert len(manager.start_calls) == 1
    assert manager.start_calls[0].metadata["tool_name"] == "probe.echo"


def test_adapter_receives_tool_completed() -> None:
    manager = RecordingLifecycleManager()
    adapter = ToolLifecycleGovernanceAdapter(manager)  # type: ignore[arg-type]
    adapter.before_tool(_hook_event(TOOL_STARTED))

    adapter.after_tool(_hook_event(TOOL_COMPLETED))

    assert len(manager.evaluate_calls) == 1
    assert manager.evaluate_calls[0].evidence is not None
    assert manager.evaluate_calls[0].evidence.status == "COMPLETED"


def test_adapter_receives_tool_failed() -> None:
    manager = RecordingLifecycleManager()
    adapter = ToolLifecycleGovernanceAdapter(manager)  # type: ignore[arg-type]
    adapter.before_tool(_hook_event(TOOL_STARTED))

    adapter.on_failure(_hook_event(TOOL_FAILED))

    assert len(manager.evaluate_calls) == 1
    assert manager.evaluate_calls[0].evidence is not None
    assert manager.evaluate_calls[0].evidence.status == "FAILED"


def test_permission_evaluator_is_called() -> None:
    manager = RecordingLifecycleManager()
    permission_evaluator = RecordingPermissionEvaluator()
    adapter = ToolLifecycleGovernanceAdapter(
        manager,  # type: ignore[arg-type]
        permission_evaluator,  # type: ignore[arg-type]
    )

    adapter.before_tool(_hook_event(TOOL_STARTED))

    assert len(permission_evaluator.calls) == 1
    assert permission_evaluator.calls[0][1].tool_name == "probe.echo"
    assert manager.start_calls[0].metadata["permission_allowed"] is True


def test_governance_lifecycle_manager_is_called() -> None:
    manager = RecordingLifecycleManager()
    permission_evaluator = RecordingPermissionEvaluator()
    adapter = ToolLifecycleGovernanceAdapter(
        manager,  # type: ignore[arg-type]
        permission_evaluator,  # type: ignore[arg-type]
    )

    adapter.before_tool(_hook_event(TOOL_STARTED))
    adapter.after_tool(_hook_event(TOOL_COMPLETED))

    assert len(manager.start_calls) == 1
    assert len(manager.evaluate_calls) == 1


def test_permission_deny_does_not_block_execution() -> None:
    manager = RecordingLifecycleManager()
    permission_evaluator = RecordingPermissionEvaluator(allowed=False)
    adapter = ToolLifecycleGovernanceAdapter(
        manager,  # type: ignore[arg-type]
        permission_evaluator,  # type: ignore[arg-type]
    )

    adapter.before_tool(_hook_event(TOOL_STARTED))
    adapter.after_tool(_hook_event(TOOL_COMPLETED))

    assert manager.start_calls[0].metadata["permission_allowed"] is False
    assert len(manager.evaluate_calls) == 1

    production_runtime = create_production_runtime()
    hook_manager = InMemoryRuntimeHookManager()
    hook_manager.register_hook(adapter)
    pipeline = AgentExecutionPipeline(
        production_runtime,
        runtime_hook_manager=hook_manager,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-tool-gov-runtime",
        agent_id="agent-tool-gov-1",
    )

    result = pipeline.run(_agent(), "tool governance runtime task", context)

    assert result.status == "COMPLETED"


def test_governance_failure_isolation() -> None:
    adapter = ToolLifecycleGovernanceAdapter(FailingLifecycleManager())  # type: ignore[arg-type]

    adapter.before_tool(_hook_event(TOOL_STARTED))
    adapter.after_tool(_hook_event(TOOL_COMPLETED))
    adapter.on_failure(_hook_event(TOOL_FAILED))


def test_assembly_optional_wiring() -> None:
    profile = replace(
        get_profile("production"),
        enable_tool_governance_hook=True,
    )
    assembly = RuntimeAssembler().assemble(RuntimeAssemblyConfig(profile=profile))

    assert assembly.tool_governance_adapter is not None
    assert assembly.runtime_hook_manager is not None
    assert assembly.agent_pipeline._runtime_hook_manager is assembly.runtime_hook_manager
    assert assembly.tool_governance_adapter in assembly.runtime_hook_manager.list_hooks()


def test_no_tool_governance_adapter_keeps_old_behavior() -> None:
    assembly = create_runtime("production")

    assert assembly.tool_governance_adapter is None
    assert assembly.governance_hook_adapter is None
    assert assembly.runtime_hook_manager is None
    assert assembly.agent_pipeline._runtime_hook_manager is None


def test_adapter_prefers_collected_evidence() -> None:
    evidence_store = InMemoryEvidenceStore()
    evidence_collector = RuntimeEvidenceCollector(evidence_store)
    collected = ExecutionEvidence(
        evidence_id="evidence-tool-gov-1",
        execution_id="exec-tool-gov-1",
        agent_id="agent-tool-gov-1",
        correlation_id="corr-tool-1",
        status="COMPLETED",
    )
    evidence_store.save(collected)

    manager = RecordingLifecycleManager()
    adapter = ToolLifecycleGovernanceAdapter(
        manager,  # type: ignore[arg-type]
        evidence_collector=evidence_collector,
    )
    adapter.before_tool(_hook_event(TOOL_STARTED))
    adapter.after_tool(_hook_event(TOOL_COMPLETED))

    assert manager.evaluate_calls[0].evidence == collected


def test_tool_lifecycle_governance_adapter_has_no_forbidden_dependencies() -> None:
    for path in _ADAPTER_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"


def test_hook_manager_dispatches_tool_failed_to_on_failure() -> None:
    hook = MagicMock()
    manager = InMemoryRuntimeHookManager()
    manager.register_hook(hook)
    manager.dispatch(_hook_event(TOOL_FAILED))

    hook.on_failure.assert_called_once()

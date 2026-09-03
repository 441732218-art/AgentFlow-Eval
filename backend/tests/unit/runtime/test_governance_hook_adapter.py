# AgentFlow Intelligence v2.0 — Governance runtime hook adapter tests (Phase 12.2)

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
from app.runtime.governance.hooks.adapter import (
    GovernanceRuntimeHookAdapter,
    governance_hook_context_from_event,
)
from app.runtime.governance.hooks.models import GovernanceHookContext
from app.runtime.governance.lifecycle.manager import GovernanceLifecycleManager
from app.runtime.governance.lifecycle.models import GovernanceLifecycleContext
from app.runtime.hooks.memory_manager import InMemoryRuntimeHookManager
from app.runtime.hooks.models import (
    EXECUTION_COMPLETED,
    EXECUTION_FAILED,
    EXECUTION_STARTED,
    RuntimeHookEvent,
)
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline

_ADAPTER_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "hooks"
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
    "PermissionEvaluator",
    "AgentRuntime",
    "ExecutionContext",
)


def _hook_event(event_type: str) -> RuntimeHookEvent:
    return RuntimeHookEvent(
        event_id="hook-event-1",
        event_type=event_type,  # type: ignore[arg-type]
        execution_id="exec-gov-hook-1",
        agent_id="agent-gov-hook-1",
        timestamp=datetime(2026, 9, 4, 1, 0, tzinfo=timezone.utc),
        payload={"task": "governance hook task", "plan_id": "plan-1"},
    )


def _agent() -> AgentDefinition:
    return AgentDefinition(
        id="agent-gov-hook-1",
        name="governance-hook-agent",
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
        raise RuntimeError("governance start failed")

    def evaluate(self, context: GovernanceLifecycleContext) -> GovernanceLifecycleContext:
        raise RuntimeError("governance evaluate failed")


def test_governance_hook_context_creation() -> None:
    context = governance_hook_context_from_event(_hook_event(EXECUTION_STARTED))

    assert context.execution_id == "exec-gov-hook-1"
    assert context.agent_id == "agent-gov-hook-1"
    assert context.event_type == EXECUTION_STARTED
    assert context.payload["task"] == "governance hook task"


def test_governance_hook_context_is_immutable() -> None:
    context = GovernanceHookContext(
        execution_id="exec-gov-hook-1",
        agent_id="agent-gov-hook-1",
        event_type=EXECUTION_STARTED,
        timestamp=datetime(2026, 9, 4, 1, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(FrozenInstanceError):
        context.event_type = EXECUTION_FAILED  # type: ignore[misc]

    updated = context.with_updates(event_type=EXECUTION_FAILED)
    assert updated.event_type == EXECUTION_FAILED
    assert context.event_type == EXECUTION_STARTED


def test_adapter_receives_execution_started() -> None:
    manager = RecordingLifecycleManager()
    adapter = GovernanceRuntimeHookAdapter(manager)  # type: ignore[arg-type]

    adapter.before_execution(_hook_event(EXECUTION_STARTED))

    assert len(manager.start_calls) == 1
    assert manager.start_calls[0].execution_id == "exec-gov-hook-1"


def test_adapter_receives_execution_completed() -> None:
    manager = RecordingLifecycleManager()
    adapter = GovernanceRuntimeHookAdapter(manager)  # type: ignore[arg-type]
    adapter.before_execution(_hook_event(EXECUTION_STARTED))

    adapter.after_execution(_hook_event(EXECUTION_COMPLETED))

    assert len(manager.evaluate_calls) == 1
    assert manager.evaluate_calls[0].evidence is not None
    assert manager.evaluate_calls[0].evidence.status == "COMPLETED"


def test_adapter_receives_execution_failed() -> None:
    manager = RecordingLifecycleManager()
    adapter = GovernanceRuntimeHookAdapter(manager)  # type: ignore[arg-type]
    adapter.before_execution(_hook_event(EXECUTION_STARTED))

    adapter.on_failure(_hook_event(EXECUTION_FAILED))

    assert len(manager.evaluate_calls) == 1
    assert manager.evaluate_calls[0].evidence is not None
    assert manager.evaluate_calls[0].evidence.status == "FAILED"


def test_lifecycle_manager_is_called_for_observation() -> None:
    manager = RecordingLifecycleManager()
    adapter = GovernanceRuntimeHookAdapter(manager)  # type: ignore[arg-type]

    adapter.before_execution(_hook_event(EXECUTION_STARTED))
    adapter.after_execution(_hook_event(EXECUTION_COMPLETED))

    assert len(manager.start_calls) == 1
    assert len(manager.evaluate_calls) == 1


def test_governance_exception_isolation() -> None:
    adapter = GovernanceRuntimeHookAdapter(FailingLifecycleManager())  # type: ignore[arg-type]

    adapter.before_execution(_hook_event(EXECUTION_STARTED))
    adapter.after_execution(_hook_event(EXECUTION_COMPLETED))
    adapter.on_failure(_hook_event(EXECUTION_FAILED))


def test_runtime_continues_after_governance_failure() -> None:
    production_runtime = create_production_runtime()
    hook_manager = InMemoryRuntimeHookManager()
    hook_manager.register_hook(
        GovernanceRuntimeHookAdapter(FailingLifecycleManager())  # type: ignore[arg-type]
    )
    pipeline = AgentExecutionPipeline(
        production_runtime,
        runtime_hook_manager=hook_manager,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-gov-hook-runtime",
        agent_id="agent-gov-hook-1",
    )

    result = pipeline.run(_agent(), "governance hook runtime task", context)

    assert result.status == "COMPLETED"


def test_assembly_optional_wiring() -> None:
    profile = replace(
        get_profile("production"),
        enable_governance_hook_adapter=True,
    )
    assembly = RuntimeAssembler().assemble(RuntimeAssemblyConfig(profile=profile))

    assert assembly.governance_hook_adapter is not None
    assert assembly.runtime_hook_manager is not None
    assert assembly.agent_pipeline._runtime_hook_manager is assembly.runtime_hook_manager
    assert assembly.governance_hook_adapter in assembly.runtime_hook_manager.list_hooks()


def test_no_governance_adapter_keeps_old_behavior() -> None:
    assembly = create_runtime("production")

    assert assembly.governance_hook_adapter is None
    assert assembly.runtime_hook_manager is None
    assert assembly.agent_pipeline._runtime_hook_manager is None


def test_adapter_prefers_collected_evidence() -> None:
    evidence_store = InMemoryEvidenceStore()
    evidence_collector = RuntimeEvidenceCollector(evidence_store)
    collected = ExecutionEvidence(
        evidence_id="evidence-gov-hook-1",
        execution_id="exec-gov-hook-1",
        agent_id="agent-gov-hook-1",
        correlation_id="corr-1",
        status="COMPLETED",
    )
    evidence_store.save(collected)

    manager = RecordingLifecycleManager()
    adapter = GovernanceRuntimeHookAdapter(
        manager,  # type: ignore[arg-type]
        evidence_collector=evidence_collector,
    )
    adapter.before_execution(_hook_event(EXECUTION_STARTED))
    adapter.after_execution(_hook_event(EXECUTION_COMPLETED))

    assert manager.evaluate_calls[0].evidence == collected


def test_governance_hook_adapter_has_no_forbidden_dependencies() -> None:
    for path in _ADAPTER_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

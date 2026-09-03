# AgentFlow Intelligence v2.0 — Runtime execution hook tests (Phase 12.1)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.hooks.memory_manager import InMemoryRuntimeHookManager
from app.runtime.hooks.models import (
    EXECUTION_COMPLETED,
    EXECUTION_FAILED,
    EXECUTION_STARTED,
    STEP_COMPLETED,
    STEP_FAILED,
    STEP_STARTED,
    RuntimeHookEvent,
)
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline

_HOOKS_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "hooks"
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
    "GovernanceLifecycleManager",
)


def _event(event_type: str = EXECUTION_STARTED) -> RuntimeHookEvent:
    return RuntimeHookEvent(
        event_id="hook-event-1",
        event_type=event_type,  # type: ignore[arg-type]
        execution_id="exec-hook-1",
        agent_id="agent-hook-1",
        payload={"task": "hook task"},
    )


def _agent() -> AgentDefinition:
    return AgentDefinition(
        id="agent-hook-1",
        name="hook-agent",
        tool_names=["probe.echo"],
    )


class RecordingHook:
    def __init__(self) -> None:
        self.events: list[str] = []

    def before_execution(self, event: RuntimeHookEvent) -> None:
        self.events.append(event.event_type)

    def after_execution(self, event: RuntimeHookEvent) -> None:
        self.events.append(event.event_type)

    def before_step(self, event: RuntimeHookEvent) -> None:
        self.events.append(event.event_type)

    def after_step(self, event: RuntimeHookEvent) -> None:
        self.events.append(event.event_type)

    def on_failure(self, event: RuntimeHookEvent) -> None:
        self.events.append(event.event_type)


class FailingHook:
    def before_execution(self, event: RuntimeHookEvent) -> None:
        raise RuntimeError("hook failed")


def test_runtime_hook_event_creation() -> None:
    event = _event()

    assert event.event_id == "hook-event-1"
    assert event.event_type == EXECUTION_STARTED
    assert event.execution_id == "exec-hook-1"
    assert event.agent_id == "agent-hook-1"
    assert event.payload["task"] == "hook task"


def test_runtime_hook_event_is_immutable() -> None:
    event = _event()

    with pytest.raises(FrozenInstanceError):
        event.event_type = EXECUTION_FAILED  # type: ignore[misc]

    updated = event.with_updates(event_type=EXECUTION_FAILED)
    assert updated.event_type == EXECUTION_FAILED
    assert event.event_type == EXECUTION_STARTED


def test_hook_registration_and_removal() -> None:
    manager = InMemoryRuntimeHookManager()
    hook = RecordingHook()

    manager.register_hook(hook)
    assert manager.list_hooks() == [hook]

    manager.remove_hook(hook)
    assert manager.list_hooks() == []


def test_dispatch_ordering() -> None:
    manager = InMemoryRuntimeHookManager()
    first = RecordingHook()
    second = RecordingHook()
    manager.register_hook(first)
    manager.register_hook(second)

    manager.dispatch(_event(EXECUTION_STARTED))

    assert first.events == [EXECUTION_STARTED]
    assert second.events == [EXECUTION_STARTED]


def test_multiple_hooks_receive_events() -> None:
    manager = InMemoryRuntimeHookManager()
    hooks = [RecordingHook() for _ in range(3)]
    for hook in hooks:
        manager.register_hook(hook)

    manager.dispatch(_event(EXECUTION_COMPLETED))

    assert all(hook.events == [EXECUTION_COMPLETED] for hook in hooks)


def test_hook_exception_isolation() -> None:
    manager = InMemoryRuntimeHookManager()
    failing = FailingHook()
    recording = RecordingHook()
    manager.register_hook(failing)
    manager.register_hook(recording)

    manager.dispatch(_event(EXECUTION_STARTED))

    assert recording.events == [EXECUTION_STARTED]


def test_pipeline_lifecycle_callbacks() -> None:
    production_runtime = create_production_runtime()
    manager = InMemoryRuntimeHookManager()
    hook = RecordingHook()
    manager.register_hook(hook)
    pipeline = AgentExecutionPipeline(
        production_runtime,
        runtime_hook_manager=manager,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-hook-pipeline",
        agent_id="agent-hook-1",
    )

    result = pipeline.run(_agent(), "hook pipeline task", context)

    assert result.status == "COMPLETED"
    assert EXECUTION_STARTED in hook.events
    assert STEP_STARTED in hook.events
    assert STEP_COMPLETED in hook.events
    assert EXECUTION_COMPLETED in hook.events


def test_pipeline_without_hook_manager_preserves_behavior() -> None:
    production_runtime = create_production_runtime()
    pipeline = AgentExecutionPipeline(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-hook-legacy",
        agent_id="agent-hook-1",
    )

    result = pipeline.run(_agent(), "legacy hook task", context)

    assert result.status == "COMPLETED"
    assert pipeline._runtime_hook_manager is None


def test_pipeline_failure_callback() -> None:
    production_runtime = create_production_runtime()
    manager = InMemoryRuntimeHookManager()
    hook = RecordingHook()
    manager.register_hook(hook)
    pipeline = AgentExecutionPipeline(
        production_runtime,
        runtime_hook_manager=manager,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-hook-fail",
        agent_id="agent-hook-1",
    )

    with patch.object(
        pipeline._execution_pipeline,
        "run",
        side_effect=RuntimeError("hook pipeline failure"),
    ):
        result = pipeline.run(_agent(), "failed hook task", context)

    assert result.status == "FAILED"
    assert STEP_FAILED in hook.events
    assert EXECUTION_FAILED in hook.events


def test_hook_manager_is_thread_safe() -> None:
    manager = InMemoryRuntimeHookManager()
    errors: list[Exception] = []

    def register_many(prefix: str) -> None:
        try:
            for _ in range(20):
                manager.register_hook(RecordingHook())
                manager.dispatch(
                    RuntimeHookEvent(
                        event_id=f"event-{prefix}",
                        event_type=EXECUTION_STARTED,
                        execution_id=f"exec-{prefix}",
                        agent_id="agent-hook-1",
                    )
                )
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=register_many, args=(f"t{i}",)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(manager.list_hooks()) == 80


def test_hooks_module_has_no_forbidden_dependencies() -> None:
    for path in _HOOKS_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

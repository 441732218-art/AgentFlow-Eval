# AgentFlow Intelligence v2.0 — Runtime Trace Hook unit tests

from __future__ import annotations

from app.runtime.context import RuntimeContext
from app.runtime.executor import AgentExecutor
from app.runtime.pipeline import ExecutionPipeline
from app.runtime.tracing import RUNTIME_TRACE_KEY, TraceHook


def _run_with_trace_hook(context: RuntimeContext, task: str = "demo task") -> None:
    pipeline = ExecutionPipeline(hooks=[TraceHook()])
    pipeline.run(context, task)


def test_before_execute_writes_trace_event() -> None:
    context = RuntimeContext(execution_id="exec-1", agent_id="agent-1")

    hook = TraceHook()
    hook.before_execute(context, "start task")

    trace = context.metadata[RUNTIME_TRACE_KEY]
    assert len(trace["events"]) == 1
    event = trace["events"][0]
    assert event["type"] == "execution.started"
    assert event["timestamp"]
    assert event["metadata"]["task"] == "start task"


def test_after_execute_writes_completed_event() -> None:
    context = RuntimeContext(execution_id="exec-2", agent_id="agent-1")

    hook = TraceHook()
    hook.after_execute(context, "done")

    trace = context.metadata[RUNTIME_TRACE_KEY]
    assert len(trace["events"]) == 1
    event = trace["events"][0]
    assert event["type"] == "execution.completed"
    assert event["metadata"]["output"] == "done"


def test_events_are_ordered_start_then_completed() -> None:
    context = RuntimeContext(execution_id="exec-3", agent_id="agent-1")

    _run_with_trace_hook(context, "ordered task")

    events = context.metadata[RUNTIME_TRACE_KEY]["events"]
    assert [event["type"] for event in events] == [
        "execution.started",
        "execution.completed",
    ]


def test_metadata_does_not_overwrite_existing_keys() -> None:
    context = RuntimeContext(
        execution_id="exec-4",
        agent_id="agent-1",
        metadata={
            "tenant": "acme",
            RUNTIME_TRACE_KEY: {"events": [{"type": "existing.event", "timestamp": "t0"}]},
        },
    )

    _run_with_trace_hook(context, "preserve me")

    assert context.metadata["tenant"] == "acme"
    events = context.metadata[RUNTIME_TRACE_KEY]["events"]
    assert events[0]["type"] == "existing.event"
    assert events[1]["type"] == "execution.started"
    assert events[2]["type"] == "execution.completed"


def test_executor_preserves_trace_on_context() -> None:
    context = RuntimeContext(execution_id="exec-5", agent_id="agent-1")
    executor = AgentExecutor()

    result = executor.execute(agent_id="agent-1", task="trace me", context=context)

    assert result.status == "SUCCESS"
    events = context.metadata[RUNTIME_TRACE_KEY]["events"]
    assert [event["type"] for event in events] == [
        "execution.started",
        "execution.completed",
    ]

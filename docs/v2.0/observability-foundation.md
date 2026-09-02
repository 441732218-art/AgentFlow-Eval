# Runtime Observability Foundation (Phase 9.5)

## Overview

Phase 9.5 adds an in-memory **runtime observation** layer for agent execution governance. This is separate from the existing `TraceHook` pipeline tracing and does not modify tracing, API, or UI layers.

## Components

| Module | Purpose |
|--------|---------|
| `observability/events.py` | `RuntimeEvent` model and `RuntimeEventType` constants |
| `observability/collector.py` | `ObservationCollector` protocol and `InMemoryObservationCollector` |
| `observability/recording.py` | `build_runtime_event()`, `record_runtime_event()` |
| `tools/invocation_event.py` | Extended `ToolInvocationEvent` with timing fields |

## RuntimeEvent

Fields: `event_type`, `timestamp`, `execution_id`, `agent_id`, `tenant_id`, `tool_name`, `status`, `duration_ms`, `metadata`.

Supported `event_type` values:

- `execution.started`
- `execution.completed`
- `tool.started`
- `tool.completed`
- `tool.failed`

## ObservationCollector

```python
collector = InMemoryObservationCollector()
execution_context = ExecutionContext(
    execution_id="exec-001",
    observation_collector=collector,
)
```

Interface:

- `record(event)` — append a `RuntimeEvent`
- `get_events()` — return all recorded events

No database or external SDK is used. `InMemoryObservationCollector` is thread-safe for test usage.

## Recording

```python
record_runtime_event(execution_context, event)
```

If no collector is attached, recording is skipped silently. Collector failures are swallowed so observation never interrupts tool execution.

## Propagation

```
ExecutionContext.observation_collector
    → pipeline/tool_step.py (tool.started / completed / failed)
    → remote_adapter.py (remote transport observation)
```

`ExecutionContext.to_remote_payload()` is unchanged — the collector is never sent to remote providers.

## Relationship to TraceHook

| Layer | Storage | Scope |
|-------|---------|-------|
| `TraceHook` (frozen) | `context.metadata["runtime_trace"]` | Pipeline hook lifecycle |
| `ObservationCollector` (new) | In-memory collector on `ExecutionContext` | Tool invocation, duration, status, errors |

Both coexist without conflict. TraceHook is not modified in this phase.

## Boundary

Allowed changes: `executor/**`, `pipeline/**`, `tools/**`, `observability/**`, tests, docs.

Frozen: `tracing/**`, `service/**`, `memory/**`, `api/**`, `applications/**`.

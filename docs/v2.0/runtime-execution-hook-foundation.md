# Runtime Execution Hook Foundation (Phase 12.1)

## Overview

Phase 12.1 introduces a **runtime lifecycle hook system** that lets observability, governance, auditing, and future extensions subscribe to execution lifecycle events without modifying core pipeline execution logic.

## Purpose

The runtime kernel needs extension points that decouple lifecycle observation from execution algorithms. The hook layer provides:

- Immutable hook event models
- Optional hook callbacks
- Thread-safe hook dispatch with failure isolation
- Optional pipeline integration

No governance enforcement, tool behavior changes, or external messaging is introduced.

## Architecture Position

```
Runtime Pipeline
        |
        v
Runtime Hook Manager
        |
        +------------------+------------------+
        |                  |                  |
     Audit            Analytics          Governance
   (future)           (future)           (future)
```

Hook events are independent from:

- `RuntimeEventEnvelope`
- `AuditRecord`
- Analytics metric models

## Components

| Module | Responsibility |
|--------|----------------|
| `hooks/models.py` | `RuntimeHookEvent` and event type constants |
| `hooks/hook.py` | `RuntimeHook` callback interface |
| `hooks/manager.py` | `RuntimeHookManager` protocol |
| `hooks/memory_manager.py` | `InMemoryRuntimeHookManager` |

## RuntimeHookEvent

| Field | Description |
|-------|-------------|
| `event_id` | Unique event identifier |
| `event_type` | Lifecycle event type |
| `execution_id` | Related execution identifier |
| `agent_id` | Related agent identifier |
| `timestamp` | Event timestamp |
| `payload` | Optional event payload |

Supported event types:

- `execution.started`, `execution.completed`, `execution.failed`
- `step.started`, `step.completed`, `step.failed`
- `tool.started`, `tool.completed`, `tool.failed`

## RuntimeHook Callbacks

| Callback | Trigger |
|----------|---------|
| `before_execution` | `execution.started` |
| `after_execution` | `execution.completed` |
| `before_step` | `step.started` |
| `after_step` | `step.completed` |
| `before_tool` | `tool.started` |
| `after_tool` | `tool.completed` |
| `on_failure` | `execution.failed`, `step.failed`, `tool.failed` |

All hook methods default to no-op.

## Dispatch Behavior

`InMemoryRuntimeHookManager.dispatch()`:

- Preserves registration order
- Is thread-safe
- Isolates hook failures (one failing hook does not stop others)
- Never propagates hook exceptions to the pipeline

## Pipeline Integration

`AgentExecutionPipeline` accepts optional `runtime_hook_manager=None`.

When provided:

| Lifecycle point | Hook event |
|-----------------|------------|
| Before strategy execution | `execution.started` |
| After successful completion | `execution.completed` |
| After execution failure | `execution.failed` |
| Before each step | `step.started` |
| After each successful step | `step.completed` |
| On step failure | `step.failed` |

When `runtime_hook_manager=None`, pipeline behavior is unchanged.

## Assembly Compatibility

`RuntimeAssembly` includes optional `runtime_hook_manager=None` for future composition. Assembly does not enable hooks by default in this phase.

## Boundary Rules

This phase **must not**:

- Execute governance enforcement
- Modify governance, tool, or policy behavior
- Change `ExecutionContext` structure
- Introduce database, Redis, Kafka, API, or external queues

## Usage

```python
from app.runtime.hooks import InMemoryRuntimeHookManager, RuntimeHook, RuntimeHookEvent
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline

class AuditHook(RuntimeHook):
    def after_execution(self, event: RuntimeHookEvent) -> None:
        ...

manager = InMemoryRuntimeHookManager()
manager.register_hook(AuditHook())

pipeline = AgentExecutionPipeline(
    production_runtime,
    runtime_hook_manager=manager,
)
```

## Testing

Unit tests live in `backend/tests/unit/runtime/test_runtime_hooks.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_runtime_hooks.py -q
pytest backend/tests/unit/runtime/ -q
```

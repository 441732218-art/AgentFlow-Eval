# Runtime Event Publisher Foundation (Phase 9.6)

## Overview

Phase 9.6 adds a decoupled **event publishing** boundary so enterprise systems can later consume agent execution audit, tool invocation, governance, and SLA events without coupling Runtime Core to external infrastructure.

No Kafka, Redis, database, or third-party observability SDK is introduced in this phase.

## Components

| Module | Purpose |
|--------|---------|
| `events/event_types.py` | `RuntimeEventType` enum |
| `events/models.py` | Publishable `RuntimeEvent` with JSON-safe payload |
| `events/publisher.py` | `RuntimeEventPublisher` protocol, `InMemoryEventPublisher` |

## RuntimeEventType

- `EXECUTION_STARTED`
- `EXECUTION_COMPLETED`
- `EXECUTION_FAILED`
- `TOOL_STARTED`
- `TOOL_COMPLETED`
- `TOOL_FAILED`

## Integration

`ExecutionContext` optionally carries `event_publisher` (default `None`).

`record_runtime_event()` in `observability/recording.py`:

1. Records to `observation_collector` when present
2. Publishes via `event_publisher` when present
3. Swallows collector/publisher failures — execution is never interrupted

`ExecutionContext.to_remote_payload()` does not expose `event_publisher` or internal collectors.

## Relationship to Phase 9.5

| Layer | Role |
|-------|------|
| `ObservationCollector` | In-process observation store |
| `RuntimeEventPublisher` | Decoupled publish boundary for downstream consumers |

Both can be attached to the same `ExecutionContext` independently.

## Boundary

Allowed: `events/**`, `executor/**`, `observability/**`, tests, docs.

Frozen: `service/**`, `tracing/**`, `memory/**`, `api/**`, `applications/**`.

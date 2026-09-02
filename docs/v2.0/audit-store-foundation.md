# Runtime Audit Store Foundation (Phase 9.7)

## Overview

Phase 9.7 adds an **audit store** persistence boundary so runtime governance events can be queried by execution or tenant scope without coupling Runtime Core to external storage.

No SQL, Redis, Kafka, or other external persistence is introduced in this phase.

## Components

| Module | Purpose |
|--------|---------|
| `audit/models.py` | Immutable `AuditRecord`, `audit_record_from_runtime_event()` |
| `audit/store.py` | `AuditEventStore` protocol |
| `audit/memory_store.py` | Thread-safe `InMemoryAuditStore` |

## AuditRecord

Fields: `id`, `event_type`, `execution_id`, `agent_id`, `tenant_id`, `timestamp`, `payload`.

Payload is JSON-serializable and excludes sensitive field names (inherited from publisher event sanitization).

## AuditEventStore

- `append(record)` — store one audit record
- `query(execution_id=None, tenant_id=None)` — filter records
- `clear()` — reset in-memory store

## Publisher Integration

`InMemoryEventPublisher(audit_store=...)` optionally appends an `AuditRecord` on every `publish()` call. Existing in-memory event buffering is unchanged. Audit append failures are swallowed and logged at debug level.

## ExecutionContext

Optional `audit_store` field (default `None`) enables governance queries from the same execution scope. `to_remote_payload()` does not expose internal stores or publishers.

## Flow

```
record_runtime_event()
    → event_publisher.publish(RuntimeEvent)
        → InMemoryEventPublisher._events
        → audit_store.append(AuditRecord)   (optional)
```

## Boundary

Allowed: `audit/**`, `events/**`, `executor/**`, `observability/**`, tests, docs.

Frozen: `service/**`, `tracing/**`, `memory/**`, `api/**`, `applications/**`.

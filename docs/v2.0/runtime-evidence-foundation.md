# Runtime Governance Evidence Layer Foundation (Phase 11.4)

## Overview

Phase 11.4 introduces a **runtime evidence aggregation boundary** that unifies execution artifacts produced by existing Runtime Kernel components into one immutable `ExecutionEvidence` record per agent execution.

Evidence collection is **read-only aggregation**. It does not modify analytics, audit, event stream, permission evaluation, or execution behavior.

## Components

| Module | Responsibility |
|--------|----------------|
| `evidence/models.py` | `ExecutionEvidence`, summary models, `PermissionDecision` |
| `evidence/store.py` | `EvidenceStore` protocol |
| `evidence/memory_store.py` | `InMemoryEvidenceStore` (thread-safe) |
| `evidence/collector.py` | `RuntimeEvidenceCollector` aggregation coordinator |

## Evidence Architecture

```
Execution completes or fails
        |
        v
RuntimeEvidenceCollector.collect()
        |
        +-- ExecutionState          -> state_snapshot
        +-- Checkpoint              -> checkpoint_summary
        +-- MemoryContext           -> memory_snapshot
        +-- RuntimeContextSnapshot  -> supplements missing summaries
        +-- AuditRecord[]           -> audit_records
        +-- RuntimeEventEnvelope[]  -> event_summary
        +-- ExecutionMetric         -> metrics_summary
        +-- PermissionDecision[]    -> permission_decisions
        |
        v
ExecutionEvidence (immutable)
        |
        v
EvidenceStore.save()
```

## ExecutionEvidence Model

| Field | Description |
|-------|-------------|
| `evidence_id` | Unique evidence record identifier |
| `execution_id` | Agent execution identifier |
| `agent_id` | Agent identifier |
| `correlation_id` | Correlation identifier when available |
| `status` | `COMPLETED`, `FAILED`, `RUNNING`, or `UNKNOWN` |
| `state_snapshot` | Immutable execution state summary |
| `checkpoint_summary` | Immutable latest checkpoint summary |
| `memory_snapshot` | Immutable runtime memory summary |
| `audit_records` | Tuple of existing audit records |
| `event_summary` | Aggregated runtime event stream summary |
| `metrics_summary` | Aggregated execution analytics summary |
| `permission_decisions` | Tuple of permission decisions |
| `created_at` | Evidence creation timestamp |

All nested structures are immutable (`frozen` dataclasses or tuples).

## Pipeline Integration

`AgentExecutionPipeline` accepts an optional `evidence_collector`:

```python
from app.runtime.evidence import InMemoryEvidenceStore, RuntimeEvidenceCollector

store = InMemoryEvidenceStore()
collector = RuntimeEvidenceCollector(store)

pipeline = AgentExecutionPipeline(
    production_runtime,
    evidence_collector=collector,
)
```

Lifecycle hooks:

| Event | Action |
|-------|--------|
| `execution.complete` | Collect and save completed evidence |
| `execution.failed` | Collect and save failed evidence |

When `evidence_collector=None`, pipeline behavior matches Phase 11.3.

## Boundary Rules

Evidence layer **must not**:

- Call `ToolExecutionEngine`
- Call `PolicyEngine`
- Create `AuditRecord` instances
- Modify event stream publishers
- Modify analytics collectors or stores

Evidence layer **only reads** artifacts already produced by runtime components.

Permission decisions may be supplied explicitly or derived from existing permission-related audit records during aggregation.

## Storage

`InMemoryEvidenceStore` provides thread-safe in-process persistence using `threading.Lock`. No database, Redis, Kafka, or external services are introduced.

## Relationship to Other Phase 11 Layers

| Layer | Role relative to evidence |
|-------|---------------------------|
| Analytics (11.1) | Source metrics summarized into `metrics_summary` |
| Event Stream (11.2) | Source events summarized into `event_summary` |
| Audit (11.3) | Source records copied into `audit_records` |

Evidence complements observability layers by producing a single governance artifact suitable for compliance review and future export boundaries.

## Testing

Unit tests live in `backend/tests/unit/runtime/test_runtime_evidence.py` and cover:

- Immutable evidence models
- Evidence store CRUD
- Thread safety
- Collector aggregation
- Pipeline completed and failed evidence collection
- Empty optional components
- Backward compatibility when `evidence_collector=None`
- Forbidden dependency scan

Run:

```bash
pytest backend/tests/unit/runtime/test_runtime_evidence.py -q
pytest backend/tests/unit/runtime/ -q
```
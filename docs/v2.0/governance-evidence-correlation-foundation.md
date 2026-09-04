# Governance Evidence Correlation Foundation (Phase 12.10)

## Overview

Phase 12.10 introduces a **standalone governance evidence correlation layer** that links execution evidence with governance decisions and evaluation snapshots.

The correlation layer is observation-only and does not modify runtime execution paths.

## Purpose

Governance evaluation produces evidence and snapshot artifacts across multiple layers. The correlation foundation records how these artifacts relate for one execution.

## Architecture Position

```
ExecutionEvidence
        |
        v
EvidenceCorrelationBuilder
        |
        v
EvidenceCorrelation
        |
        v
GovernanceSnapshot
```

Correlation records preserve references to:

- Execution evidence
- Governance decisions
- Governance evaluation snapshots

## Components

| Module | Responsibility |
|--------|----------------|
| `governance/evidence_correlation/models.py` | `EvidenceCorrelation`, `GovernanceEvidenceReference` |
| `governance/evidence_correlation/builder.py` | `EvidenceCorrelationBuilder`, `DefaultEvidenceCorrelationBuilder` |
| `governance/evidence_correlation/store.py` | `EvidenceCorrelationStore` protocol |
| `governance/evidence_correlation/memory_store.py` | `InMemoryEvidenceCorrelationStore` |

## EvidenceCorrelation

Immutable correlation record:

| Field | Description |
|-------|-------------|
| `correlation_id` | Unique correlation identifier |
| `execution_id` | Execution identifier |
| `evidence_id` | Linked execution evidence identifier |
| `decision_id` | Linked governance decision identifier |
| `snapshot_id` | Linked governance snapshot identifier |
| `references` | Detailed artifact references |
| `created_at` | Correlation creation timestamp |
| `metadata` | Additional correlation metadata |

## GovernanceEvidenceReference

Immutable artifact reference:

| Field | Description |
|-------|-------------|
| `reference_id` | Unique reference identifier |
| `reference_type` | `evidence`, `decision`, or `snapshot` |
| `execution_id` | Execution identifier |
| `artifact_id` | Referenced artifact identifier |
| `metadata` | Reference metadata |

## EvidenceCorrelationBuilder

`DefaultEvidenceCorrelationBuilder` aggregates optional artifacts:

- `ExecutionEvidence`
- `GovernanceDecision`
- `GovernanceSnapshot`

Disabled mode returns a minimal correlation with `correlation_enabled=False`.

## EvidenceCorrelationStore

Protocol methods:

- `save()`
- `get()`
- `list_by_execution()`
- `list_all()`
- `remove()`
- `clear()`

`InMemoryEvidenceCorrelationStore` provides thread-safe in-memory storage.

## Assembly Placeholder

`RuntimeAssembly` includes optional:

- `governance_evidence_correlation_store=None`

Default assembly behavior is unchanged.

## Responsibility Boundary

This phase **must not**:

- Modify `AgentRuntime` execution flow
- Modify `AgentExecutionPipeline` control flow
- Modify `ToolExecutionEngine` behavior
- Modify `PolicyEngine` or `PermissionEvaluator` logic
- Block runtime execution or mutate execution state
- Introduce database, Redis, Kafka, or external services

Existing runtime behavior remains backward compatible.

## Future Integration Point

Future phases may:

- Build correlations automatically from orchestrator and snapshot pipelines
- Feed correlations into enterprise governance reporting
- Wire correlation store through assembly profiles

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_evidence_correlation.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_evidence_correlation.py -q
pytest backend/tests/unit/runtime/ -q
```

## Usage

```python
from app.runtime.governance.evidence_correlation import (
    DefaultEvidenceCorrelationBuilder,
    EvidenceCorrelationBuildRequest,
    InMemoryEvidenceCorrelationStore,
)

builder = DefaultEvidenceCorrelationBuilder()
store = InMemoryEvidenceCorrelationStore()
correlation = builder.build(
    EvidenceCorrelationBuildRequest(
        execution_id="exec-1",
        evidence=execution_evidence,
        snapshot=governance_snapshot,
    )
)
store.save(correlation)
```

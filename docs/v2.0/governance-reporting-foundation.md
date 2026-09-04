# Governance Reporting Foundation (Phase 11.10)

## Overview

Phase 11.10 introduces **governance reporting primitives** that aggregate existing governance artifacts into immutable `GovernanceReport` records. This phase is read-only aggregation and storage only; it does not integrate with runtime execution.

## Purpose

Governance stakeholders need a consolidated view of execution evidence, decisions, enforcement actions, and optional approval outcomes. The reporting layer provides:

- Immutable report models
- Report generation from existing artifacts
- In-memory report storage

No API, UI, database, or external reporting service is introduced.

## Architecture Position

```
ExecutionEvidence
        |
        v
GovernanceDecision
        |
        v
GovernanceAction
        |
        v
ApprovalDecision (optional)
        |
        v
GovernanceReportGenerator
        |
        v
GovernanceReport
        |
        v
ReportStore
```

Phase 11.10 stops at report generation and storage. No wiring into `AgentRuntime`, `AgentExecutionPipeline`, or enforcement paths is performed.

## Components

| Module | Responsibility |
|--------|----------------|
| `reporting/models.py` | `GovernanceReport` immutable model |
| `reporting/generator.py` | `GovernanceReportGenerator` aggregation |
| `reporting/store.py` | `ReportStore` protocol |
| `reporting/memory_store.py` | `InMemoryReportStore` (thread-safe) |

## GovernanceReport

| Field | Description |
|-------|-------------|
| `report_id` | Unique report identifier |
| `execution_id` | Related execution identifier |
| `agent_id` | Optional agent identifier |
| `risk_level` | `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` |
| `decision_status` | Governance decision status |
| `approval_status` | Optional approval outcome |
| `summary` | Human-readable summary string |
| `evidence_count` | Aggregated evidence item count |
| `created_at` | Report creation timestamp |
| `metadata` | Optional metadata dictionary |

## Risk Mapping

| Condition | Risk level |
|-----------|------------|
| `ALLOW` decision / action | `LOW` |
| `WARN` decision / action | `MEDIUM` |
| Permission denials in evidence | `MEDIUM` (when otherwise low) |
| Failed execution evidence | `HIGH` |
| `DENY` / `BLOCK` | `CRITICAL` |
| `DENY` with approved override | `HIGH` |

## Generator Behavior

`GovernanceReportGenerator.generate()` accepts:

- `ExecutionEvidence`
- `GovernanceDecision`
- `GovernanceAction`
- `ApprovalDecision` (optional)

It returns a new `GovernanceReport` without modifying source objects.

## Boundary Rules

This phase **must not**:

- Modify runtime execution components
- Call `PolicyEngine`, `PermissionEvaluator`, or approval stores directly
- Integrate with evidence collectors or query services
- Introduce database, Redis, Kafka, or external services

## Usage

```python
from app.runtime.governance import GovernanceReportGenerator, InMemoryReportStore

generator = GovernanceReportGenerator()
store = InMemoryReportStore()

report = generator.generate(evidence, decision, action, approval)
store.create(report)
```

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_reporting.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_reporting.py -q
pytest backend/tests/unit/runtime/ -q
```
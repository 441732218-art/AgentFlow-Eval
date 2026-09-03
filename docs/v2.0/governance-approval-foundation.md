# Governance Approval Workflow Foundation (Phase 11.9)

## Overview

Phase 11.9 introduces **governance approval workflow primitives** for tracking manual review of governance outcomes. This phase is storage-only and standalone: it does not integrate with runtime execution, enforcement, or policy evaluation.

## Purpose

Some governance decisions require human approval before downstream action. The approval layer provides:

- Immutable approval request records
- Immutable approval decision records
- In-memory store for pending requests and decision history

No API, UI, database, or external workflow engine is introduced.

## Architecture Position

```
GovernanceDecision
        |
        v
ApprovalRequest (PENDING)
        |
        v
ApprovalDecision (APPROVE / REJECT)
        |
        v
ApprovalRequest (APPROVED / REJECTED)
```

Future phases may connect approval outcomes to enforcement. Phase 11.9 stops at approval storage boundaries.

## Components

| Module | Responsibility |
|--------|----------------|
| `approval/models.py` | `ApprovalRequest`, `ApprovalDecision` |
| `approval/store.py` | `ApprovalStore` protocol |
| `approval/memory_store.py` | `InMemoryApprovalStore` (thread-safe) |

## ApprovalRequest

| Field | Description |
|-------|-------------|
| `request_id` | Unique approval request identifier |
| `execution_id` | Related execution identifier |
| `policy_id` | Optional related policy identifier |
| `decision_id` | Optional related governance decision identifier |
| `reason` | Why approval is required |
| `status` | `PENDING`, `APPROVED`, `REJECTED`, or `EXPIRED` |
| `created_at` | Request creation timestamp |
| `updated_at` | Last update timestamp |
| `metadata` | Optional metadata dictionary |

## ApprovalDecision

| Field | Description |
|-------|-------------|
| `request_id` | Target approval request |
| `decision` | `APPROVE` or `REJECT` |
| `approver` | Approver identity |
| `reason` | Decision rationale |
| `timestamp` | Decision timestamp |
| `metadata` | Optional metadata dictionary |

## Store Behavior

| Method | Behavior |
|--------|----------|
| `create` | Create or replace a request by `request_id` |
| `get` | Return one request |
| `update` | Replace an existing request |
| `list_pending` | Return requests with `PENDING` status |
| `record_decision` | Append decision history and update request status |
| `get_decisions` | Return decision history for a request |

Recording `APPROVE` sets request status to `APPROVED`. Recording `REJECT` sets status to `REJECTED`.

## Boundary Rules

This phase **must not**:

- Modify `AgentRuntime` or `AgentExecutionPipeline`
- Call `GovernanceEvaluator`, `GovernanceEnforcer`, or `PolicyEngine`
- Integrate with evidence collection or query layers
- Introduce database, Redis, Kafka, or external workflow services

## Usage

```python
from app.runtime.governance import (
    ApprovalDecision,
    ApprovalRequest,
    InMemoryApprovalStore,
)

store = InMemoryApprovalStore()
store.create(
    ApprovalRequest(
        request_id="approval-1",
        execution_id="exec-1",
        reason="deny decision requires review",
    )
)

store.record_decision(
    ApprovalDecision(
        request_id="approval-1",
        decision="APPROVE",
        approver="security-reviewer",
        reason="exception approved",
    )
)
```

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_approval.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_approval.py -q
pytest backend/tests/unit/runtime/ -q
```

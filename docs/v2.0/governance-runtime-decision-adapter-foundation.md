# Governance Runtime Decision Adapter Foundation (Phase 13.3)

## Overview

Phase 13.3 introduces a **standalone governance runtime decision adapter layer** that converts normalized governance decisions into `GovernanceExecutionEffect` semantics and associated resolution types.

The adapter is observation-only and does not modify runtime execution paths.

## Purpose

Governance decisions arrive with statuses such as `ALLOW`, `WARN`, `DENY`, `BLOCK`, and `REQUIRE_APPROVAL`.

The runtime decision adapter translates these statuses into execution effect and resolution semantics for downstream governance contract and resolver layers.

## Architecture Position

```
GovernanceRuntimeDecisionRequest
        |
        v
GovernanceRuntimeDecisionAdapter.adapt()
        |
        v
GovernanceRuntimeDecisionResult
        |
        +--> GovernanceExecutionEffect
        +--> Resolution semantics
```

## Components

| Module | Responsibility |
|--------|----------------|
| `governance/runtime_adapter/models.py` | Request/result models |
| `governance/runtime_adapter/adapter.py` | `GovernanceRuntimeDecisionAdapter` protocol |
| `governance/runtime_adapter/memory_adapter.py` | `InMemoryGovernanceRuntimeDecisionAdapter` |

## GovernanceRuntimeDecisionRequest

Immutable adaptation input:

| Field | Description |
|-------|-------------|
| `decision_id` | Governance decision identifier |
| `execution_id` | Execution identifier |
| `decision_status` | Normalized decision status |
| `target` | Adaptation target descriptor |
| `reason` | Human-readable explanation |
| `agent_id` | Optional agent identifier |
| `evidence_reference` | Optional evidence reference |
| `metadata` | Additional request metadata |

## GovernanceRuntimeDecisionResult

Immutable adaptation output:

| Field | Description |
|-------|-------------|
| `result_id` | Unique adaptation result identifier |
| `decision_id` | Source decision identifier |
| `execution_id` | Execution identifier |
| `effect` | Adapted `GovernanceExecutionEffect` |
| `effect_action_type` | Effect action type |
| `resolution_type` | Normalized resolution type |
| `executable` | Whether execution may proceed |
| `metadata` | Additional result metadata |

## Decision Mapping

| Decision Status | Effect Action | Resolution Type | Executable |
|-----------------|---------------|-----------------|------------|
| `ALLOW` | `ALLOW` | `CONTINUE` | Yes |
| `WARN` | `WARN` | `CONTINUE_WITH_WARNING` | Yes |
| `DENY` | `BLOCK` | `BLOCK_REQUEST` | No |
| `BLOCK` | `BLOCK` | `BLOCK_REQUEST` | No |
| `REQUIRE_APPROVAL` | `REQUIRE_APPROVAL` | `WAIT_APPROVAL` | No |

## InMemoryGovernanceRuntimeDecisionAdapter

Thread-safe in-memory implementation:

- `adapt()`
- `get_result()`
- `list_results()`
- `clear()`
- Disabled mode returns `ALLOW` / `CONTINUE` without blocking

## Assembly Placeholder

`RuntimeAssembly` includes optional:

- `governance_runtime_decision_adapter=None`

Default assembly behavior is unchanged. No runtime execution wiring is introduced in this phase.

## Responsibility Boundary

This phase **must not**:

- Modify `AgentRuntime`, `AgentExecutionPipeline`, or `ToolExecutionEngine`
- Modify `ExecutionContext`, `PolicyEngine`, or `PermissionEvaluator`
- Block runtime execution or intercept pipeline control flow
- Introduce database, Redis, Kafka, API, UI, or external services

Existing runtime behavior remains backward compatible.

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_runtime_decision_adapter.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_runtime_decision_adapter.py -q
pytest backend/tests/unit/runtime/ -q
```

## Usage

```python
from app.runtime.governance.runtime_adapter import (
    GovernanceRuntimeDecisionRequest,
    InMemoryGovernanceRuntimeDecisionAdapter,
)

adapter = InMemoryGovernanceRuntimeDecisionAdapter()
result = adapter.adapt(
    GovernanceRuntimeDecisionRequest(
        decision_id="decision-1",
        execution_id="exec-1",
        decision_status="WARN",
        target="execution:exec-1",
        reason="risk detected",
    )
)
```

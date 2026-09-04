# Governance Execution Contract Foundation (Phase 13.1)

## Overview

Phase 13.1 introduces a **standalone governance execution contract layer** that records governance execution effects without modifying runtime execution behavior.

The contract layer is observation-only and preserves immutable execution records for future enterprise governance integration.

## Purpose

Governance routing and orchestration produce execution effects describing intended actions such as allow, warn, block, or require approval.

The execution contract records these effects as immutable observations without calling runtime engines, tools, or policy evaluators.

## Architecture Position

```
GovernanceExecutionEffect
        |
        v
GovernanceExecutionContract.execute()
        |
        v
GovernanceExecutionRecord
        |
        v
(Future enterprise governance integration)
```

## Components

| Module | Responsibility |
|--------|----------------|
| `governance/execution/models.py` | `GovernanceExecutionEffect`, `GovernanceExecutionRecord` |
| `governance/execution/contract.py` | `GovernanceExecutionContract` protocol |
| `governance/execution/memory_executor.py` | `InMemoryGovernanceExecutionContract` |

## GovernanceExecutionEffect

Immutable governance execution effect descriptor:

| Field | Description |
|-------|-------------|
| `effect_id` | Unique effect identifier |
| `decision_id` | Source governance decision identifier |
| `action_type` | Execution action type |
| `target` | Effect target descriptor |
| `reason` | Human-readable explanation |
| `evidence_reference` | Optional evidence reference |
| `metadata` | Additional effect metadata |

### Allowed Action Types

| Action Type | Description |
|-------------|-------------|
| `ALLOW` | Allow execution to proceed |
| `WARN` | Proceed with warning |
| `BLOCK` | Block execution |
| `REQUIRE_APPROVAL` | Require approval before proceeding |

## GovernanceExecutionContract Protocol

```python
class GovernanceExecutionContract(Protocol):
    def execute(self, effect: GovernanceExecutionEffect) -> GovernanceExecutionRecord: ...
    def get_execution(self, effect_id: str) -> GovernanceExecutionRecord | None: ...
    def list_executions(self) -> list[GovernanceExecutionRecord]: ...
    def clear(self) -> None: ...
```

## InMemoryGovernanceExecutionContract

Thread-safe in-memory implementation:

- Records immutable execution observations
- Supports `execute()`, `get_execution()`, `list_executions()`, and `clear()`
- Disabled mode returns `ALLOW` with `applied=False`
- No external dependencies

## Responsibility Boundary

This phase **must not**:

- Modify `AgentRuntime` execution flow
- Modify `AgentExecutionPipeline` control flow
- Call `ToolExecutionEngine`
- Call `PolicyEngine` or `PermissionEvaluator`
- Block or mutate runtime execution
- Introduce database, Redis, Kafka, API, or external services

Existing runtime behavior remains backward compatible.

## Future Integration Point

Future phases may:

- Feed routed governance outcomes into execution effects
- Connect execution records to approval workflows and audit systems
- Wire execution contract through assembly profiles

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_execution_contract.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_execution_contract.py -q
pytest backend/tests/unit/runtime/ -q
```

## Usage

```python
from app.runtime.governance.execution import (
    GovernanceExecutionEffect,
    InMemoryGovernanceExecutionContract,
)

contract = InMemoryGovernanceExecutionContract()
record = contract.execute(
    GovernanceExecutionEffect(
        effect_id="effect-1",
        decision_id="decision-1",
        action_type="WARN",
        target="execution:exec-1",
        reason="risk detected",
    )
)
```

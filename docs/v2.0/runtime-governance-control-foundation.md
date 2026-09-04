# Runtime Governance Control Layer Foundation (Phase 12.4)

## Overview

Phase 12.4 introduces a **runtime governance control layer** that translates governance decisions into control decisions suitable for future runtime enforcement orchestration.

This phase defines the control model and evaluation bridge only. No runtime execution behavior is changed.

## Purpose

Governance evaluation produces `GovernanceDecision` records with statuses `ALLOW`, `WARN`, and `DENY`. The control layer normalizes these into runtime-oriented control outcomes with explicit action types.

The control layer prepares governance for future enforcement integration without modifying existing runtime execution paths.

## Architecture Position

```
GovernanceDecision
        |
        v
GovernanceController
        |
        v
GovernanceControlDecision
        |
        v
(Future enforcement integration)
```

## Components

| Module | Responsibility |
|--------|----------------|
| `governance/control/models.py` | `GovernanceControlDecision` |
| `governance/control/controller.py` | `GovernanceController` protocol |
| `governance/control/memory_controller.py` | `InMemoryGovernanceController` |

## GovernanceControlDecision

Immutable control decision derived from a governance decision:

| Field | Description |
|-------|-------------|
| `control_id` | Unique control decision identifier |
| `execution_id` | Execution identifier |
| `decision_status` | Control outcome status |
| `action_type` | Recommended runtime action |
| `reason` | Human-readable explanation |
| `timestamp` | Control evaluation timestamp |
| `metadata` | Additional control metadata |

### Control Decision Statuses

| Status | Description |
|--------|-------------|
| `ALLOW` | Execution may proceed |
| `WARN` | Execution may proceed with warning |
| `REQUIRE_APPROVAL` | Reserved for future approval-gated control |
| `BLOCK` | Execution should be blocked |

## Decision Mapping

`InMemoryGovernanceController` maps governance decisions as follows:

| Governance Decision | Control Status | Action Type |
|--------------------|----------------|-------------|
| `ALLOW` | `ALLOW` | `ALLOW` |
| `WARN` | `WARN` | `WARN` |
| `DENY` | `BLOCK` | `BLOCK` |

`REQUIRE_APPROVAL` is defined on the control model for future approval workflow integration.

## GovernanceController Protocol

```python
class GovernanceController(Protocol):
    def evaluate(self, decision: GovernanceDecision) -> GovernanceControlDecision:
        ...
```

Implementations translate governance decisions into control decisions without modifying runtime execution.

## InMemoryGovernanceController

Thread-safe in-memory implementation:

- Records evaluated control decisions
- Supports enable/disable via `enabled` flag
- When disabled, returns `ALLOW` control decisions without blocking
- Provides `list_decisions()` and `clear()` for observation and testing

## Boundary Rules

This phase **must not**:

- Modify `AgentRuntime` execution flow
- Modify `AgentExecutionPipeline` control flow
- Modify `ToolExecutionEngine` behavior
- Modify `PermissionEvaluator` logic
- Modify `GovernanceLifecycleManager` logic
- Introduce database, Redis, Kafka, API, or external services

Existing runtime behavior remains backward compatible.

## Usage

```python
from app.runtime.governance.control import InMemoryGovernanceController
from app.runtime.governance.models import GovernanceDecision

controller = InMemoryGovernanceController()
control = controller.evaluate(governance_decision)
```

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_control.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_control.py -q
pytest backend/tests/unit/runtime/ -q
```

# Runtime Governance Orchestrator Foundation (Phase 12.10)

## Overview

Phase 12.10 introduces a **standalone governance runtime orchestrator** that coordinates existing governance components into unified orchestration results.

The orchestrator coordinates decisions only. It does not execute runtime actions, block agent execution, call tools, or modify execution context.

## Purpose

Prior governance phases provide specialized layers:

- Decision routing
- Enforcement pipeline
- Runtime enforcement binding
- Policy execution binding
- Governance reporting

The orchestrator composes these optional components through dependency injection and returns a normalized `GovernanceExecutionResult`.

## Architecture Position

```
GovernanceExecutionRequest
        |
        v
InMemoryGovernanceRuntimeOrchestrator
        |
        +--> Enforcement Pipeline (optional)
        +--> Enforcement Binder (optional)
        +--> Policy Binder (optional)
        +--> Decision Router (optional)
        +--> Report Generator (optional)
        |
        v
GovernanceExecutionResult
        |
        v
(Future runtime integration)
```

## Components

| Module | Responsibility |
|--------|----------------|
| `governance/orchestrator/models.py` | `GovernanceExecutionRequest`, `GovernanceExecutionResult` |
| `governance/orchestrator/orchestrator.py` | `GovernanceRuntimeOrchestrator` protocol |
| `governance/orchestrator/memory_orchestrator.py` | `InMemoryGovernanceRuntimeOrchestrator` |

## GovernanceExecutionRequest

Normalized orchestration input:

| Field | Description |
|-------|-------------|
| `execution_id` | Execution identifier |
| `decision_status` | Governance decision status |
| `enforcement_status` | Optional enforcement status |
| `policy_id` | Optional policy identifier |
| `metadata` | Additional orchestration metadata |

Report generation requires orchestration metadata containing `evidence`, `governance_decision`, and `governance_action`.

## GovernanceExecutionResult

Immutable orchestration result:

| Field | Description |
|-------|-------------|
| `execution_id` | Execution identifier |
| `route_type` | Final routing path |
| `action` | Recommended orchestration action |
| `enforcement_applied` | Whether enforcement pipeline ran |
| `approval_required` | Whether approval is required |
| `blocked` | Whether route indicates blocking |
| `report_generated` | Whether a report was generated |
| `metadata` | Aggregated orchestration metadata |

## GovernanceRuntimeOrchestrator Protocol

```python
class GovernanceRuntimeOrchestrator(Protocol):
    def execute(self, request: GovernanceExecutionRequest) -> GovernanceExecutionResult:
        ...
```

## InMemoryGovernanceRuntimeOrchestrator

Thread-safe in-memory implementation with optional dependency injection:

| Dependency | Role |
|------------|------|
| `decision_router` | Route governance outcomes |
| `enforcement_pipeline` | Evaluate gate/enforcement outcomes |
| `enforcement_binder` | Bind enforcement results |
| `policy_binder` | Bind policy versions to executions |
| `report_generator` | Generate reports when artifacts are supplied |

Supports:

- `execute()`
- `get_result()`
- `list_results()`
- `clear()`

Disabled mode returns `ALLOW` / `CONTINUE` without applying enforcement or generating reports.

## Coordination Flow

1. Optionally evaluate enforcement pipeline from orchestration input
2. Optionally bind enforcement results
3. Optionally bind policy versions
4. Optionally route through decision router (fallback routing if router absent)
5. Optionally generate report when artifacts are present in metadata

All coordination is observation-only.

## Assembly Placeholder

`RuntimeAssembly` includes optional:

- `governance_orchestrator=None`

Default assembly behavior is unchanged.

## Responsibility Boundary

This phase **must not**:

- Execute runtime or block `AgentRuntime`
- Modify `AgentExecutionPipeline` control flow
- Modify `ToolExecutionEngine` behavior
- Modify `PolicyEngine` or `PermissionEvaluator` logic
- Call tools or modify execution context
- Introduce database, Redis, Kafka, API, or external services

Existing runtime behavior remains backward compatible.

## Future Integration Point

Future phases may:

- Wire orchestrator dependencies through assembly profiles
- Feed lifecycle outcomes into `GovernanceExecutionRequest`
- Connect orchestration results to runtime enforcement activation

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_orchestrator.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_orchestrator.py -q
pytest backend/tests/unit/runtime/ -q
```

## Usage

```python
from app.runtime.governance.orchestrator import (
    GovernanceExecutionRequest,
    InMemoryGovernanceRuntimeOrchestrator,
)
from app.runtime.governance.routing import InMemoryGovernanceDecisionRouter

orchestrator = InMemoryGovernanceRuntimeOrchestrator(
    decision_router=InMemoryGovernanceDecisionRouter(),
)
result = orchestrator.execute(
    GovernanceExecutionRequest(
        execution_id="exec-1",
        decision_status="WARN",
    )
)
```

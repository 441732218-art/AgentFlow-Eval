# Governance Lifecycle Orchestration Foundation (Phase 11.11)

## Overview

Phase 11.11 introduces a **governance lifecycle orchestration layer** that composes existing governance components into a coordinated workflow. This phase provides orchestration primitives only; it does not integrate with runtime execution.

## Purpose

Governance processing spans multiple standalone foundations:

- Decision evaluation
- Enforcement translation
- Optional approval resolution
- Report generation

The lifecycle manager coordinates these steps through immutable context and result models without modifying source artifacts or invoking runtime tools.

## Architecture Position

```
Policy (registered rules)
        |
        v
GovernanceDecision
        |
        v
Approval (optional)
        |
        v
GovernanceAction
        |
        v
GovernanceReport
```

Orchestration flow:

```
GovernanceLifecycleContext
        |
        v
GovernanceLifecycleManager.start()
        |
        v
GovernanceLifecycleManager.evaluate()
        |
        v
GovernanceLifecycleManager.apply_action()
        |
        v
GovernanceLifecycleManager.generate_report()
        |
        v
GovernanceLifecycleResult
```

## Components

| Module | Responsibility |
|--------|----------------|
| `lifecycle/models.py` | `GovernanceLifecycleContext`, `GovernanceLifecycleResult` |
| `lifecycle/manager.py` | `GovernanceLifecycleManager` orchestration |
| `lifecycle/runtime_lifecycle.py` | Existing `RuntimeGovernanceLifecycle` (tool execution governance) |

The existing `RuntimeGovernanceLifecycle` remains available through the `lifecycle` package for backward-compatible imports.

## GovernanceLifecycleContext

Partial lifecycle state is supported. Fields:

| Field | Description |
|-------|-------------|
| `execution_id` | Execution identifier |
| `evidence` | Optional `ExecutionEvidence` |
| `decision` | Optional `GovernanceDecision` |
| `action` | Optional `GovernanceAction` |
| `approval` | Optional `ApprovalDecision` |
| `report` | Optional `GovernanceReport` |
| `metadata` | Lifecycle metadata dictionary |

## GovernanceLifecycleManager

Coordinates:

| Component | Role |
|-----------|------|
| `GovernanceEvaluator` / `InMemoryGovernanceEngine` | Evaluate evidence |
| `GovernanceEnforcer` | Translate decision to action |
| `ApprovalStore` (optional) | Resolve approval history |
| `GovernanceReportGenerator` | Build final report |

Methods:

| Method | Behavior |
|--------|----------|
| `start` | Initialize lifecycle metadata |
| `evaluate` | Attach governance decision |
| `apply_action` | Attach enforcement action |
| `generate_report` | Produce report and lifecycle result |

## Boundary Rules

This phase **must not**:

- Modify `AgentRuntime` or `AgentExecutionPipeline`
- Execute tools through `ToolExecutionEngine`
- Call `PolicyEngine` or `PermissionEvaluator` from orchestration code
- Introduce database, Redis, Kafka, API, or external workflow services

Orchestration is read-only with respect to source governance artifacts.

## Usage

```python
from app.runtime.governance import (
    GovernanceLifecycleContext,
    GovernanceLifecycleManager,
    InMemoryGovernanceEngine,
    InMemoryGovernanceEnforcer,
    GovernanceReportGenerator,
)

manager = GovernanceLifecycleManager(
    decision_engine=InMemoryGovernanceEngine(),
    enforcer=InMemoryGovernanceEnforcer(),
    report_generator=GovernanceReportGenerator(),
)

context = GovernanceLifecycleContext(
    execution_id="exec-1",
    evidence=evidence,
)
context = manager.start(context)
context = manager.evaluate(context)
context = manager.apply_action(context)
context, result = manager.generate_report(context)
```

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_lifecycle.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_lifecycle.py -q
pytest backend/tests/unit/runtime/ -q
```
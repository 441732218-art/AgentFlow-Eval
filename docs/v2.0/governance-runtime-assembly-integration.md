# Governance Runtime Assembly Integration (Phase 13.9)

## Overview

Phase 13.9 integrates the governance runtime plane into `RuntimeAssembly` as optional, profile-controlled composition. Assembly wires governance components through constructor injection only; it does not execute governance logic or modify runtime execution paths.

## Architecture

```
RuntimeAssembly
        |
        + Execution Runtime
        |     ProductionRuntime
        |     AgentRuntime
        |     AgentExecutionPipeline
        |
        + Governance Runtime Plane (optional)
                |
                + GovernanceRuntimeDecisionAdapter
                |
                + GovernanceRuntimeOrchestrator
                |       + GovernanceDecisionRouter
                |       + RuntimeEnforcementPipeline
                |       + RuntimeEnforcementBinder
                |       + PolicyExecutionBinder
                |
                + GovernanceConfigurationRegistry
                |
                + GovernanceSnapshotBuilder
                |       + SnapshotStore
                |
                + EvidenceCorrelationBuilder
                |       + EvidenceCorrelationStore
                |
                + GovernanceExecutionContract
                |
                + GovernanceEffectResolver
```

## Dependency Flow

1. `RuntimeProfile.enable_governance_runtime` controls whether the governance stack is composed.
2. `RuntimeAssembler._build_governance_runtime_stack()` instantiates in-memory governance components.
3. Dependencies are injected through constructor parameters (for example, `InMemoryGovernanceRuntimeOrchestrator(decision_router=...)`).
4. Composed references are exposed on `RuntimeAssembly` for callers that opt into governance observation.
5. `AgentRuntime` and `AgentExecutionPipeline` construction is unchanged; governance fields are not auto-wired into execution.

## Optional Injection Model

All governance fields on `RuntimeAssembly` default to `None`:

| Field | Component |
|-------|-----------|
| `governance_decision_router` | `InMemoryGovernanceDecisionRouter` |
| `governance_runtime_orchestrator` | `InMemoryGovernanceRuntimeOrchestrator` |
| `governance_configuration_registry` | `InMemoryGovernanceConfigurationRegistry` |
| `governance_snapshot_builder` | `DefaultGovernanceSnapshotBuilder` |
| `governance_snapshot_store` | `InMemoryGovernanceSnapshotStore` |
| `governance_evidence_correlation_builder` | `DefaultEvidenceCorrelationBuilder` |
| `governance_evidence_correlation_store` | `InMemoryEvidenceCorrelationStore` |
| `governance_execution_contract` | `InMemoryGovernanceExecutionContract` |
| `governance_effect_resolver` | `InMemoryGovernanceEffectResolver` |
| `governance_runtime_decision_adapter` | `InMemoryGovernanceRuntimeDecisionAdapter` |

Existing assembly behavior is preserved when `enable_governance_runtime=False`.

## Profiles

| Profile | `enable_governance_runtime` |
|---------|----------------------------|
| `development` | `True` |
| `production` | `True` |
| `testing` | `False` (default) |

The testing profile keeps assembly lightweight by omitting the governance runtime stack.

## Why Runtime Execution Is Untouched

- Assembly composition is additive and observation-oriented.
- No changes to `AgentRuntime`, `AgentExecutionPipeline`, `ToolExecutionEngine`, `ExecutionContext`, `PolicyEngine`, or `PermissionEvaluator`.
- Governance components are composed and exposed; callers choose when to invoke them.
- Direct runtime construction (`AgentRuntime(create_production_runtime())`) remains valid without governance stack wiring.

## Usage

```python
from app.runtime.assembly import create_runtime

assembly = create_runtime("production")

orchestrator = assembly.governance_runtime_orchestrator
decision_adapter = assembly.governance_runtime_decision_adapter
snapshot_builder = assembly.governance_snapshot_builder
```

When governance runtime assembly is disabled, these attributes are `None`.

## Boundaries

- No database, Redis, Kafka, or external service dependencies.
- No automatic governance enforcement during agent or pipeline execution.
- Assembly module remains free of application, API, and legacy core imports.

## Tests

Unit tests live in `backend/tests/unit/runtime/test_governance_runtime_assembly.py`.

```bash
pytest backend/tests/unit/runtime/test_governance_runtime_assembly.py -q
pytest backend/tests/unit/runtime/ -q
git diff --check
```

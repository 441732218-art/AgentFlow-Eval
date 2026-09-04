# Runtime Assembly Governance Integration Foundation (Phase 11.12)

## Overview

Phase 11.12 extends the **Runtime Assembly** layer to compose observability and governance capabilities alongside the existing execution runtime stack. This phase updates dependency wiring only; it does not change runtime component internals or execution behavior.

## Purpose

Prior phases introduced standalone foundations for analytics, event streaming, audit, evidence, and governance lifecycle orchestration. Assembly now optionally wires these components into `RuntimeAssembly` and `AgentExecutionPipeline` based on profile configuration.

## Architecture Position

```
Runtime Assembly
        |
        +-- Execution Runtime
        |     +-- ProductionRuntime
        |     +-- AgentRuntime
        |     +-- AgentExecutionPipeline
        |
        +-- Observability
        |     +-- RuntimeAnalyticsCollector
        |     +-- EventPublisher
        |     +-- RuntimeAuditRecorder
        |     +-- RuntimeEvidenceCollector
        |
        +-- Governance
              +-- GovernanceLifecycleManager
```

## Extended RuntimeAssembly Fields

| Field | Description |
|-------|-------------|
| `analytics_collector` | Optional pipeline analytics collector |
| `event_publisher` | Optional runtime event stream publisher |
| `audit_recorder` | Optional unified audit recorder |
| `evidence_collector` | Optional governance evidence collector |
| `governance_lifecycle_manager` | Optional governance lifecycle orchestrator |

All fields remain optional. When disabled by profile, values are `None`.

## Profile Behavior

| Profile | Analytics | Event stream | Audit recorder | Evidence | Governance lifecycle |
|---------|-----------|--------------|----------------|----------|----------------------|
| `development` | enabled | enabled | enabled | enabled | enabled |
| `production` | enabled | enabled | enabled | enabled | enabled |
| `testing` | disabled | disabled | disabled | disabled | disabled |

The `testing` profile keeps registries enabled while leaving stores and governance composition disabled for lightweight test runs.

## Pipeline Wiring

When enabled by profile, assembly passes shared component instances to `AgentExecutionPipeline`:

- `analytics_collector`
- `event_publisher`
- `audit_recorder`
- `evidence_collector`

`AgentRuntime` receives the same optional `audit_recorder` instance when enabled.

`GovernanceLifecycleManager` is composed on `RuntimeAssembly` only. It is not integrated into pipeline execution in this phase.

## Backward Compatibility

Direct construction continues to work unchanged:

```python
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.agent.runtime import AgentRuntime
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline

production_runtime = create_production_runtime()
agent_runtime = AgentRuntime(production_runtime)
agent_pipeline = AgentExecutionPipeline(production_runtime)
```

Optional components default to `None`, preserving pre-integration behavior.

## Boundary Rules

Assembly wiring **must not**:

- Modify `AgentRuntime` or `AgentExecutionPipeline` execution logic
- Change governance component behavior
- Introduce database, Redis, Kafka, API, or external services

Assembly only constructs and connects in-memory component instances.

## Usage

```python
from app.runtime.assembly import create_runtime

assembly = create_runtime("production")

pipeline = assembly.agent_pipeline
analytics = assembly.analytics_collector
lifecycle = assembly.governance_lifecycle_manager
```

## Testing

Unit tests live in:

- `backend/tests/unit/runtime/test_runtime_assembly.py`
- `backend/tests/unit/runtime/test_runtime_assembly_integration.py`

Run:

```bash
pytest backend/tests/unit/runtime/test_runtime_assembly_integration.py -q
pytest backend/tests/unit/runtime/ -q
```
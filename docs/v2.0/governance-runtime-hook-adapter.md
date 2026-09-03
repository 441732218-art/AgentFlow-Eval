# Governance Runtime Hook Adapter Foundation (Phase 12.2)

## Overview

Phase 12.2 introduces a **governance runtime hook adapter** that bridges the runtime lifecycle hook system with governance lifecycle orchestration. The adapter observes runtime events and triggers governance observation workflows without affecting execution outcomes.

## Purpose

Runtime hooks provide lifecycle extension points. Governance lifecycle orchestration evaluates evidence and produces decisions and reports. The adapter connects these layers for observation-only workflows.

No execution blocking, DENY enforcement, or pipeline control flow changes are introduced.

## Architecture Position

```
Runtime Pipeline
        |
        v
Runtime Hook Manager
        |
        v
GovernanceRuntimeHookAdapter
        |
        v
GovernanceLifecycleManager
        |
        v
Decision / Report (observation only)
```

## Components

| Module | Responsibility |
|--------|----------------|
| `governance/hooks/models.py` | `GovernanceHookContext` |
| `governance/hooks/adapter.py` | `GovernanceRuntimeHookAdapter` |

## GovernanceHookContext

Immutable governance-specific view of a runtime hook event:

| Field | Description |
|-------|-------------|
| `execution_id` | Execution identifier |
| `agent_id` | Agent identifier |
| `event_type` | Runtime hook event type |
| `timestamp` | Event timestamp |
| `payload` | Event payload dictionary |

`GovernanceHookContext` is separate from `RuntimeHookEvent` to maintain governance boundary clarity.

## Lifecycle Mapping

| Runtime hook | Governance action |
|--------------|-------------------|
| `execution.started` | `GovernanceLifecycleManager.start()` |
| `execution.completed` | `GovernanceLifecycleManager.evaluate()` |
| `execution.failed` | `GovernanceLifecycleManager.evaluate()` |

Evaluation uses collected evidence when available via `RuntimeEvidenceCollector`; otherwise a minimal observation evidence snapshot is built from the hook payload.

## Non-Blocking Requirement

Governance adapter failures are swallowed:

- Hook exceptions do not propagate to the pipeline
- Agent execution continues unchanged
- Execution state is not modified by governance observation failures

The adapter does not call `apply_action()` or perform enforcement.

## Assembly Integration

`RuntimeAssembly` includes optional:

- `governance_hook_adapter`
- `runtime_hook_manager`

Enabled only when profile flag `enable_governance_hook_adapter=True` and `governance_lifecycle_manager` is present.

| Profile | Default |
|---------|---------|
| `development` | disabled (optional) |
| `production` | disabled (optional) |
| `testing` | disabled |

Default assembly behavior is unchanged.

## Boundary Rules

This phase **must not**:

- Block or alter runtime execution results
- Enforce DENY decisions
- Modify `GovernanceEvaluator` or `GovernanceEnforcer` logic
- Introduce database, Redis, Kafka, API, or external services

## Usage

```python
from dataclasses import replace

from app.runtime.assembly import RuntimeAssembler, RuntimeAssemblyConfig, get_profile
from app.runtime.governance.hooks import GovernanceRuntimeHookAdapter
from app.runtime.hooks import InMemoryRuntimeHookManager

profile = replace(get_profile("production"), enable_governance_hook_adapter=True)
assembly = RuntimeAssembler().assemble(RuntimeAssemblyConfig(profile=profile))
```

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_hook_adapter.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_hook_adapter.py -q
pytest backend/tests/unit/runtime/ -q
```

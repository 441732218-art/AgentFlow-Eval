# Governance Runtime Activation Layer (Phase 13.10)

## Overview

Phase 13.10 introduces an optional **Governance Runtime Activation Layer** on top of Phase 13.9 assembly composition. The activation layer decides whether governance runtime should be activated for an execution lifecycle event without modifying runtime execution behavior.

## Activation Layer Position

```
RuntimeAssembly
        |
        + Execution Runtime
        |     ProductionRuntime
        |     AgentRuntime
        |     AgentExecutionPipeline
        |
        + Governance Runtime Stack (Phase 13.9)
        |     Orchestrator, Router, Snapshot, Evidence, Contract, Resolver, Adapter
        |
        + Governance Activation Layer (Phase 13.10)
              InMemoryGovernanceRuntimeActivator
```

The activation layer sits at the boundary between assembly composition and optional governance invocation. Callers may invoke `activate()` when a runtime lifecycle event occurs; assembly only composes the activator reference.

## Relationship to RuntimeAssembly

| Field | Component |
|-------|-----------|
| `governance_runtime_activator` | `InMemoryGovernanceRuntimeActivator` |

Wiring is controlled by `RuntimeProfile.enable_governance_activation`:

| Profile | Enabled |
|---------|---------|
| `development` | `True` |
| `production` | `True` |
| `testing` | `False` |

When disabled, `governance_runtime_activator` remains `None`. Existing assembly fields and execution wiring are unchanged.

## Components

| Module | Responsibility |
|--------|----------------|
| `activation/models.py` | `GovernanceActivationRequest`, `GovernanceActivationResult` |
| `activation/activator.py` | `GovernanceRuntimeActivator` protocol |
| `activation/memory_activator.py` | `InMemoryGovernanceRuntimeActivator` |

### Activation Behavior

**Enabled (`enabled=True`):**

```python
GovernanceActivationResult(
    activated=True,
    governance_enabled=True,
    message="governance runtime activated",
)
```

**Disabled (`enabled=False`):**

```python
GovernanceActivationResult(
    activated=False,
    governance_enabled=False,
    message="governance runtime activation disabled",
)
```

## Why Observation-Only

The activation layer:

- Returns activation decisions only
- Does not execute runtime actions, tool calls, or policy enforcement
- Does not block or modify execution results
- Records activation history for inspection

This preserves the governance plane as an observation and decision boundary, not an execution rewrite.

## Why the Execution Kernel Is Untouched

Phase 13.10 explicitly does **not** modify:

- `AgentRuntime`
- `AgentExecutionPipeline` core flow
- `ToolExecutionEngine`
- `PolicyEngine`
- `PermissionEvaluator`
- `ExecutionContext`

Assembly creates and exposes `governance_runtime_activator`; callers opt in when to call `activate()`. No new runtime dependencies are injected into execution paths.

## Usage

```python
from app.runtime.assembly import create_runtime
from app.runtime.governance.activation import GovernanceActivationRequest

assembly = create_runtime("production")
activator = assembly.governance_runtime_activator

if activator is not None:
    result = activator.activate(
        GovernanceActivationRequest(
            execution_id="exec-1",
            runtime_context={"agent_id": "agent-1"},
        )
    )
    assert result.activated is True
```

## Boundaries

- No database, Redis, Kafka, or external API dependencies
- No direct runtime blocking or execution result mutation
- No automatic wiring into `AgentRuntime` or `AgentExecutionPipeline`

## Tests

Unit tests live in `backend/tests/unit/runtime/test_governance_activation.py`.

```bash
pytest backend/tests/unit/runtime/test_governance_activation.py -q
pytest backend/tests/unit/runtime/ -q
git diff --check
```

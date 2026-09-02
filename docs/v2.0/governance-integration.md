# Runtime Governance Integration (Phase 9.9)

## Overview

Phase 9.9 unifies Phase 9.5–9.8 into a single **RuntimeGovernanceLifecycle** that coordinates policy, observation, event publishing, and audit without duplicating subsystem logic.

## Components

| Module | Purpose |
|--------|---------|
| `governance/lifecycle.py` | `RuntimeGovernanceLifecycle` orchestrator |
| `governance/middleware.py` | `use_governance_lifecycle()` guard |
| `governance/hooks.py` | Lifecycle phase identifiers |

## Governed Flow

```
ToolExecutionEngine.execute()
    → use_governance_lifecycle(context)?
        → RuntimeGovernanceLifecycle.run_tool_execution()
            → before_tool_execution (tool.started)
            → evaluate_policy
            → denied → tool.policy.denied → PolicyDeniedError
            → adapter.execute()
            → after_tool_success (tool.completed)
            → after_tool_failure (tool.failed)
    → legacy path (unchanged when governance_lifecycle is None)
```

All recording uses existing `record_runtime_event()`, which forwards to:

- `ObservationCollector`
- `RuntimeEventPublisher`
- `AuditStore` (via publisher wiring)

## ExecutionContext

Optional `governance_lifecycle` field (default `None`). Existing fields remain backward compatible:

- `observation_collector`
- `event_publisher`
- `audit_store`
- `policy_engine`

`to_remote_payload()` continues to expose only trace-safe execution identifiers.

## Backward Compatibility

When `governance_lifecycle` is `None`:

- `ToolExecutionEngine.execute()` signature unchanged
- Pipeline `tool_step` retains legacy observation recording
- Engine retains inline policy evaluation

When `governance_lifecycle` is attached, the lifecycle owns tool.started/completed/failed and policy.denied to avoid duplicate events.

## Boundary

Allowed: `governance/**`, `executor/**`, `tools/**`, `pipeline/**`, `observability/**`, `events/**`, `audit/**`, `policy/**`, tests, docs.

Frozen: `service/**`, `tracing/**`, `memory/**`, `api/**`, `applications/**`, `core/**`.

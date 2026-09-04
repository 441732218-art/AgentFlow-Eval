# Runtime Policy Enforcement Foundation (Phase 9.8)

## Overview

Phase 9.8 adds a **policy decision boundary** so enterprise runtimes can deny tool execution before adapters or providers are invoked.

## Components

| Module | Purpose |
|--------|---------|
| `policy/models.py` | `PolicyDecision`, `PolicyDeniedError` |
| `policy/rules.py` | Built-in blocked-tool rule helpers |
| `policy/engine.py` | `PolicyEngine` protocol, `InMemoryPolicyEngine` |

## PolicyDecision

Fields: `allowed`, `policy_name`, `reason`, `metadata`.

## InMemoryPolicyEngine

- Default allow when tool is not blocked
- Deny when tool name is in `blocked_tools`

Example:

```python
InMemoryPolicyEngine(blocked_tools=["dangerous.tool"])
```

## Execution Flow

```
ToolExecutionEngine.execute()
    â†?PolicyEngine.evaluate(context, tool_definition)
    â†?denied: publish tool.policy.denied + raise PolicyDeniedError
    â†?allowed: adapter.execute(...)
```

When `policy_engine` is `None`, existing behavior is unchanged.

Policy evaluation exceptions fail open (allow) and are logged at debug level.

## Event Integration

Denied executions publish `tool.policy.denied` through the existing `record_runtime_event()` path, which forwards to:

- `ObservationCollector` (optional)
- `RuntimeEventPublisher` (optional)
- `AuditStore` via publisher wiring (optional)

## ExecutionContext

Optional `policy_engine` field (default `None`). Not exposed in `to_remote_payload()`.

## Boundary

Allowed: `policy/**`, `tools/**`, `executor/**`, `events/**`, `audit/**`, tests, docs.

Frozen: `service/**`, `tracing/**`, `memory/**`, `api/**`, `applications/**`.
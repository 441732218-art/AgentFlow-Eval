# Execution Context Governance (Phase 9.4)

## Overview

Enterprise Agent Runtime governance introduces a unified **ExecutionContext** that travels with every agent run and is propagated to tool invocations, including remote HTTP providers.

## ExecutionContext

Defined in `backend/app/runtime/executor/execution_context.py`.

| Field | Type | Description |
|-------|------|-------------|
| `execution_id` | `str` | Unique identifier for the agent run |
| `agent_id` | `str \| None` | Agent performing the run |
| `tenant_id` | `str \| None` | Tenant scope |
| `user_id` | `str \| None` | End-user scope |
| `metadata` | `dict` | Opaque governance metadata (defaults to `{}`) |

The model is intentionally free of business-domain fields (no trade, CRM, or email naming).

## Propagation Chain

```
AgentExecutor
    â†?ensure_execution_context(RuntimeContext)
    â†?ExecutionPipeline
    â†?ToolExecutionEngine.execute(..., context=ExecutionContext)
    â†?ToolExecutorAdapter.execute(..., execution_context=...)
    â†?RemoteToolExecutorAdapter â†?HttpRemoteToolClient
```

When no execution context is available, existing behavior is preserved (optional parameter defaults to `None`).

## Remote HTTP Payload

Remote tool requests now include a top-level `context` object when execution context is present:

```json
{
  "name": "example.remote",
  "arguments": {},
  "context": {
    "execution_id": "exec-001",
    "agent_id": "sales-agent",
    "tenant_id": "tenant-a",
    "user_id": "user-001"
  }
}
```

Rules:

- `None` fields are omitted from `context`
- Credentials and secrets are never included in the payload body
- Authentication remains in HTTP headers via `CredentialResolver`

## ToolInvocationEvent

`backend/app/runtime/tools/invocation_event.py` defines an in-memory event model for future observability wiring. Phase 9.4 does not connect it to databases, message queues, or external telemetry.

## Boundary

Changes are limited to:

- `backend/app/runtime/executor/**`
- `backend/app/runtime/pipeline/**`
- `backend/app/runtime/tools/**`

Runtime Service, Memory, Application Provider, and API layers remain frozen.
# Tool Lifecycle Governance Foundation (Phase 12.3)

## Overview

Phase 12.3 introduces a **tool lifecycle governance observation layer** that connects tool execution lifecycle events with the runtime hook system, permission evaluation, and governance lifecycle orchestration.

The adapter observes tool invocations and records permission and governance metadata without affecting execution outcomes.

## Purpose

Tool execution produces lifecycle signals (`tool.started`, `tool.completed`, `tool.failed`). Governance needs to observe these signals alongside permission decisions to evaluate tool usage patterns.

This phase creates the observation bridge only. No enforcement is performed.

## Architecture Position

```
Tool Execution
        |
        v
Runtime Hook Manager
        |
        v
ToolLifecycleGovernanceAdapter
        |
        +--> Permission Evaluation (observation only)
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
| `governance/tool_hooks/models.py` | `ToolGovernanceHookContext` |
| `governance/tool_hooks/adapter.py` | `ToolLifecycleGovernanceAdapter` |

## ToolGovernanceHookContext

Immutable governance-specific view of a tool lifecycle hook event:

| Field | Description |
|-------|-------------|
| `execution_id` | Execution identifier |
| `agent_id` | Agent identifier |
| `tool_name` | Tool being invoked |
| `event_type` | Runtime hook event type |
| `timestamp` | Event timestamp |
| `metadata` | Additional event metadata |

`ToolGovernanceHookContext` is separate from `RuntimeHookEvent` to maintain governance boundary clarity.

## Lifecycle Mapping

| Runtime hook | Actions |
|--------------|---------|
| `tool.started` | `PermissionEvaluator.evaluate_tool_access()` (record only), then `GovernanceLifecycleManager.start()` |
| `tool.completed` | `GovernanceLifecycleManager.evaluate()` |
| `tool.failed` | `GovernanceLifecycleManager.evaluate()` |

Evaluation uses collected evidence when available via `RuntimeEvidenceCollector`; otherwise a minimal observation evidence snapshot is built from the hook payload.

## Permission Integration

The adapter may call `PermissionEvaluator.evaluate_tool_access()` for observation:

- Permission results are recorded in lifecycle metadata
- Audit records are written via `RuntimeAuditRecorder.record_permission_event()` when available
- DENY decisions are **not** raised as errors
- Tool execution is **not** blocked by the adapter

## Governance Integration

The adapter connects to `GovernanceLifecycleManager` using only:

- `start()`
- `evaluate()`

The adapter does **not** call `apply_action()`.

When audit recording is available, governance decisions are recorded via `RuntimeAuditRecorder.record_governance_event()`.

## Non-Blocking Requirement

Tool governance adapter failures are swallowed:

- Hook exceptions do not propagate to the pipeline
- Permission DENY observations do not stop tool execution
- Agent execution continues unchanged
- Execution state is not modified by governance observation failures

## Assembly Integration

`RuntimeAssembly` includes optional:

- `tool_governance_adapter`
- `runtime_hook_manager` (shared with execution governance adapter when both enabled)

Enabled only when profile flag `enable_tool_governance_hook=True`, `governance_lifecycle_manager` is present, and `permission_evaluator` is available.

| Profile | Default |
|---------|---------|
| `development` | disabled (optional) |
| `production` | disabled (optional) |
| `testing` | disabled |

Default assembly behavior is unchanged.

## Boundary Rules

This phase **must not**:

- Block or alter tool execution results
- Modify `ToolExecutionEngine` behavior
- Enforce DENY decisions or call `apply_action()`
- Modify `PermissionEvaluator`, `GovernanceEvaluator`, or `GovernanceEnforcer` logic
- Introduce database, Redis, Kafka, API, or external services

## Usage

```python
from dataclasses import replace

from app.runtime.assembly import RuntimeAssembler, RuntimeAssemblyConfig, get_profile
from app.runtime.governance.tool_hooks import ToolLifecycleGovernanceAdapter

profile = replace(get_profile("production"), enable_tool_governance_hook=True)
assembly = RuntimeAssembler().assemble(RuntimeAssemblyConfig(profile=profile))
```

## Testing

Unit tests live in `backend/tests/unit/runtime/test_tool_lifecycle_governance.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_tool_lifecycle_governance.py -q
pytest backend/tests/unit/runtime/ -q
```
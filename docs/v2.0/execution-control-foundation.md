# Execution Control Foundation (Phase 10.6)

## Overview

Phase 10.6 adds enterprise execution control on top of the Phase 10.5 execution strategy boundary. Retry and failure policies are applied through a dedicated controller before results are aggregated by the strategy.

## Architecture

```
ExecutionPlan
        ↓
SequentialExecutionStrategy
        ↓
ExecutionController.execute_step()
        ↓
RetryPolicy (per-step attempts)
        ↓
StepExecutor.execute_step()
        ↓
FailurePolicy (plan-level STOP / CONTINUE)
        ↓
StepControlOutcome
        ↓
ExecutionStrategyResult
```

## Components

| Component | Responsibility |
|-----------|----------------|
| `RetryPolicy` | Decide whether to retry a failed step attempt |
| `DefaultRetryPolicy` | `max_attempts=1` means no retry |
| `FailurePolicy` | Decide plan behavior after a step fails |
| `DefaultFailurePolicy` | Default action is `STOP` |
| `ExecutionController` | Apply retry + failure policies around one step call |
| `SequentialExecutionStrategy` | Delegate each step to `ExecutionController` |

## Default Behavior

- **Retry:** `max_attempts=1` — single attempt, no retry (backward compatible with Phase 10.5)
- **Failure:** `STOP` — halt plan execution on first step failure

## Future Extensions

The policy abstractions support future enterprise controls without changing the strategy protocol or pipeline API:

- Exponential backoff retry
- Error-type-specific retry decisions
- Compensation / rollback on failure
- Partial success reporting policies

## Boundary

- `ExecutionContext` is unchanged
- `AgentRuntime` API is unchanged
- Planner and `ExecutionStrategy` protocol are unchanged
- Control policies are strategy-internal dependencies
- No applications, API, service, memory, or tracing coupling

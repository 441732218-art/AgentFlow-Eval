# Durable Execution / Checkpoint Foundation (Phase 10.8)

## Overview

Phase 10.8 adds durable execution checkpoints on top of Phase 10.7 execution state persistence. Checkpoints capture step-level recovery points and provide a foundation for execution resume and future durable backends.

## Architecture

```
AgentExecutionPipeline.run()
        â†?CheckpointManager.save_checkpoint()     execution_start
        â†?ExecutionStrategy.execute_plan()
        â†?_CheckpointTrackingStepExecutor         before_step / after_step / step_failed
        â†?CheckpointManager.get_resume_point()
        â†?CheckpointManager.plan_for_resume()     resume foundation
```

## Components

| Component | Responsibility |
|-----------|----------------|
| `Checkpoint` | Immutable durable recovery point |
| `CheckpointStore` | Save / get / list / delete checkpoints |
| `InMemoryCheckpointStore` | Thread-safe in-memory implementation |
| `CheckpointManager` | Checkpoint creation, latest lookup, resume plan filtering |
| `AgentExecutionPipeline` | Optional `checkpoint_store` and `resume_from_checkpoint_id` |

## Checkpoint Fields

- `checkpoint_id`
- `execution_id`
- `plan_id`
- `step_id`
- `state_snapshot` â€?runtime recovery payload such as task, status, and completed steps
- `created_at`
- `metadata` â€?checkpoint phase markers such as `before_step` or `execution_completed`

## Resume Foundation

When `resume_from_checkpoint_id` is supplied:

1. Load the checkpoint from `CheckpointStore`
2. Restore task and completed step history from `state_snapshot`
3. Filter the plan to remaining steps via `CheckpointManager.plan_for_resume()`
4. Continue execution from the next uncompleted step

## Default Behavior

When no `checkpoint_store` is configured, pipeline behavior remains unchanged from Phase 10.7.

## Future Extensions

The checkpoint store protocol enables future durable backends without changing agent or runtime service APIs:

- Database-backed checkpoint persistence
- Cross-process workflow recovery
- Long-running agent execution restart

## Boundary

- `ExecutionContext` is unchanged and does not expose checkpoint storage
- `AgentRuntime` API is unchanged
- Planner, execution strategy, and controller layers are unchanged
- No database or application-layer coupling
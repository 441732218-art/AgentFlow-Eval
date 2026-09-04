# Runtime Assembly and Dependency Composition Foundation (Phase 10.15)

## Overview

Phase 10.15 introduces an optional **runtime assembly layer** that composes existing Runtime Kernel components into a production-ready dependency graph without changing internal behavior of `AgentRuntime`, `AgentExecutionPipeline`, `ToolExecutionEngine`, or `RuntimeGovernanceLifecycle`.

Assembly is additive: callers may continue constructing components directly.

## Components

| Module | Responsibility |
|--------|----------------|
| `assembly/models.py` | `RuntimeProfile`, `RuntimeAssemblyConfig`, `RuntimeAssembly` |
| `assembly/profiles.py` | Named profiles: `development`, `production`, `testing` |
| `assembly/assembler.py` | `RuntimeAssembler`, `create_runtime()` |

## Runtime Composition Architecture

```
RuntimeProfile
      �?RuntimeAssembler.assemble()
      �?┌─────────────────────────────────────────────────────────────�?�?RuntimeAssembly                                             �?�?                                                            �?�? ProductionRuntime  �?create_production_runtime(config)     �?�?      �?                                                    �?�? AgentRuntime(production_runtime, registries, evaluator)    �?�? AgentExecutionPipeline(production_runtime, optional stores)�?�?                                                            �?�? Optional in-memory components (profile-controlled):      �?�?   AgentRegistry, ToolRegistry, PermissionEvaluator         �?�?   ExecutionStateStore, CheckpointStore                     �?�?   MemoryContextManager, RuntimeContextManager              �?�?   RuntimeCorrelationManager                                �?└─────────────────────────────────────────────────────────────�?```

## Dependency Ownership

| Component | Owner | Created when |
|-----------|-------|--------------|
| `ProductionRuntime` | Assembly | Always |
| `AgentRuntime` | Assembly | Always; receives optional registry/evaluator refs |
| `AgentExecutionPipeline` | Assembly | Always; optional stores passed per profile |
| `InMemoryAgentRegistry` | Assembly | `profile.enable_agent_registry` |
| `InMemoryToolRegistry` | Assembly | `profile.enable_tool_registry` |
| `PermissionEvaluator` | Assembly | `profile.enable_permission_evaluator` |
| `InMemoryExecutionStateStore` | Assembly | `profile.enable_execution_state` |
| `InMemoryCheckpointStore` | Assembly | `profile.enable_checkpoint` |
| `MemoryContextManager` | Assembly | `profile.enable_memory_context` |
| `RuntimeContextManager` | Assembly | `profile.enable_runtime_context` |
| `RuntimeCorrelationManager` | Assembly | `profile.enable_correlation` |

`PermissionEvaluator` shares the `ProductionRuntime.policy_engine` instance. Optional pipeline stores are wired only on `RuntimeAssembly.agent_pipeline`; `AgentRuntime` continues to use its internal default pipeline unless callers route execution through the assembled pipeline explicitly.

## Profiles

| Profile | Environment | Governance | Optional pipeline stores | Permission evaluator |
|---------|-------------|------------|--------------------------|--------------------|
| `development` | development | enabled | all enabled | enabled |
| `production` | production | enabled | all enabled | enabled |
| `testing` | test | disabled | disabled | disabled |

Registries remain enabled in the `testing` profile so wiring can be verified with minimal overhead.

## Production Assembly Flow

```python
from app.runtime.assembly import create_runtime

assembly = create_runtime("production")

agent_runtime = assembly.agent_runtime
agent_pipeline = assembly.agent_pipeline
production_runtime = assembly.production_runtime
```

Steps performed by `RuntimeAssembler`:

1. Resolve `RuntimeProfile` (default: production).
2. Build `RuntimeConfig` from profile flags.
3. Call `create_production_runtime(config)`.
4. Instantiate optional in-memory registries, stores, and managers.
5. Construct `PermissionEvaluator` when enabled.
6. Construct `AgentRuntime` with supported dependencies.
7. Construct `AgentExecutionPipeline` with optional pipeline dependencies.
8. Return `RuntimeAssembly` containing all references.

## Boundaries

- No changes to `applications/**`, `api/**`, `service/**`, legacy `memory/**`, `tracing/**`, or `core/**`.
- No database, LLM, or external service dependencies.
- Direct `AgentRuntime(create_production_runtime())` construction remains valid.
- Assembly layer does not auto-wire `ToolInvocationGuard`; that remains an explicit Phase 10.14 integration step for production HTTP paths.

## Usage

```python
from app.runtime.assembly import RuntimeAssembler, RuntimeAssemblyConfig, get_profile

assembly = RuntimeAssembler().assemble(
    RuntimeAssemblyConfig(profile=get_profile("development"))
)
```

```python
from app.runtime.assembly import create_runtime

assembly = create_runtime("testing")
assert assembly.state_store is None
assert assembly.agent_registry is not None
```

## Tests

`backend/tests/unit/runtime/test_runtime_assembly.py` covers profile creation, component wiring, disabled optional components, backward-compatible direct construction, and forbidden dependency scanning.
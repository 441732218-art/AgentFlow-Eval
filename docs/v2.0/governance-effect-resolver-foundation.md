# Governance Effect Resolver Foundation (Phase 13.2)

## Overview

Phase 13.2 introduces a **standalone governance effect resolver layer** that translates `GovernanceExecutionEffect` records into normalized runtime resolution semantics.

The resolver does not execute runtime actions or modify the runtime kernel.

## Purpose

Governance execution effects describe intended actions such as allow, warn, block, or require approval.

The resolver normalizes these effects into resolution types suitable for future runtime integration while remaining observation-only in this phase.

## Architecture Position

```
GovernanceExecutionEffect
        |
        v
GovernanceEffectResolver.resolve()
        |
        v
GovernanceEffectResolution
        |
        v
(Future runtime integration)
```

## Components

| Module | Responsibility |
|--------|----------------|
| `governance/resolver/models.py` | `GovernanceEffectResolution` |
| `governance/resolver/resolver.py` | `GovernanceEffectResolver` protocol |
| `governance/resolver/memory_resolver.py` | `InMemoryGovernanceEffectResolver` |

## GovernanceEffectResolution

Immutable normalized resolution record:

| Field | Description |
|-------|-------------|
| `resolution_id` | Unique resolution identifier |
| `effect_id` | Source effect identifier |
| `resolution_type` | Normalized resolution type |
| `executable` | Whether execution may proceed |
| `reason` | Human-readable explanation |
| `metadata` | Additional resolution metadata |

## Resolution Mapping

| Effect Action | Resolution Type | Executable |
|---------------|-----------------|------------|
| `ALLOW` | `CONTINUE` | Yes |
| `WARN` | `CONTINUE_WITH_WARNING` | Yes |
| `BLOCK` | `BLOCK_REQUEST` | No |
| `REQUIRE_APPROVAL` | `WAIT_APPROVAL` | No |

## GovernanceEffectResolver Protocol

```python
class GovernanceEffectResolver(Protocol):
    def resolve(self, effect: GovernanceExecutionEffect) -> GovernanceEffectResolution: ...
    def get_resolution(self, resolution_id: str) -> GovernanceEffectResolution | None: ...
    def list_resolutions(self) -> list[GovernanceEffectResolution]: ...
    def clear(self) -> None: ...
```

## InMemoryGovernanceEffectResolver

Thread-safe in-memory implementation:

- Records immutable resolution results
- Disabled mode returns `CONTINUE` with `executable=True`
- No external dependencies

## Responsibility Boundary

This phase **must not**:

- Execute runtime actions
- Modify `AgentRuntime` or `AgentExecutionPipeline`
- Call `ToolExecutionEngine`, `PolicyEngine`, or `PermissionEvaluator`
- Introduce database, Redis, Kafka, API, or external services

Existing runtime behavior remains backward compatible.

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_effect_resolver.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_effect_resolver.py -q
pytest backend/tests/unit/runtime/ -q
```

## Usage

```python
from app.runtime.governance.execution import GovernanceExecutionEffect
from app.runtime.governance.resolver import InMemoryGovernanceEffectResolver

resolver = InMemoryGovernanceEffectResolver()
resolution = resolver.resolve(governance_execution_effect)
```

# Governance Configuration Foundation (Phase 13.1)

## Overview

Phase 13.1 introduces the first foundation component of the **Enterprise Governance Plane**: a standalone governance configuration registry for storing immutable configuration records.

This phase defines configuration models and in-memory storage only. No runtime execution behavior is changed.

## Purpose

Enterprise governance requires named, scoped configuration records that describe how governance should behave per environment, tenant, or agent scope.

The configuration foundation provides a registry for storing and retrieving these records without coupling to runtime execution paths.

## Architecture Position

```
GovernanceConfiguration
        |
        v
GovernanceConfigurationRegistry
        |
        v
InMemoryGovernanceConfigurationRegistry
        |
        v
(Future Enterprise Governance Plane integration)
```

## Components

| Module | Responsibility |
|--------|----------------|
| `governance/configuration/models.py` | `GovernanceConfiguration`, `GovernanceConfigurationScope` |
| `governance/configuration/registry.py` | `GovernanceConfigurationRegistry` protocol |
| `governance/configuration/memory_registry.py` | `InMemoryGovernanceConfigurationRegistry` |

## GovernanceConfiguration

Immutable governance configuration record:

| Field | Description |
|-------|-------------|
| `configuration_id` | Unique configuration identifier |
| `name` | Human-readable configuration name |
| `description` | Configuration description |
| `enabled` | Whether the configuration is enabled |
| `environment` | Target environment name |
| `metadata` | Additional configuration metadata |
| `scope` | Optional configuration scope |

## GovernanceConfigurationScope

Immutable scope descriptor:

| Field | Description |
|-------|-------------|
| `scope_id` | Unique scope identifier |
| `agent_id` | Optional agent identifier |
| `tenant_id` | Optional tenant identifier |
| `tags` | Optional scope tags |

## GovernanceConfigurationRegistry Protocol

```python
class GovernanceConfigurationRegistry(Protocol):
    def register(self, configuration: GovernanceConfiguration) -> None: ...
    def get(self, configuration_id: str) -> GovernanceConfiguration | None: ...
    def list_all(self) -> list[GovernanceConfiguration]: ...
    def remove(self, configuration_id: str) -> None: ...
```

## InMemoryGovernanceConfigurationRegistry

Thread-safe in-memory implementation:

- Stores immutable configuration records by `configuration_id`
- Supports register, get, list_all, and remove
- Provides `clear()` for tests
- No external dependencies

## Assembly Placeholder

`RuntimeAssembly` includes optional:

- `governance_configuration_registry=None`

Default assembly behavior is unchanged.

## Responsibility Boundary

This phase **must not**:

- Modify `AgentRuntime` execution flow
- Modify `AgentExecutionPipeline` control flow
- Modify `ToolExecutionEngine` behavior
- Modify `PolicyEngine` or `PermissionEvaluator` logic
- Introduce database, Redis, Kafka, API, or external services
- Change runtime execution behavior

Existing runtime behavior remains backward compatible.

## Future Integration Point

Future Enterprise Governance Plane phases may:

- Resolve active configuration by environment and scope
- Feed configuration into orchestrator and policy binding layers
- Wire configuration registry through assembly profiles

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_configuration.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_configuration.py -q
pytest backend/tests/unit/runtime/ -q
```

## Usage

```python
from app.runtime.governance.configuration import (
    GovernanceConfiguration,
    InMemoryGovernanceConfigurationRegistry,
)

registry = InMemoryGovernanceConfigurationRegistry()
registry.register(
    GovernanceConfiguration(
        configuration_id="config-prod",
        name="Production Governance",
        description="Production governance defaults",
        enabled=True,
        environment="production",
    )
)
```

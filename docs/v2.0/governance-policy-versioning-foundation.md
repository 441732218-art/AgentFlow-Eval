# Governance Policy Versioning Foundation (Phase 11.8)

## Overview

Phase 11.8 introduces a **governance policy version registry** for storing and retrieving policy version metadata. This phase is additive and standalone: it does not bind policies into runtime execution, evaluation, or enforcement paths.

## Purpose

Runtime governance needs a durable notion of policy versions before policies can be selected, audited, or rolled out. The versioning layer provides:

- Immutable policy version records
- Registry storage and lookup
- Latest active version resolution with semantic version ordering

Policy evaluation and enforcement remain unchanged in this phase.

## Architecture Position

```
GovernancePolicyVersion
        |
        v
GovernancePolicyRegistry
        |
        +-- register / get / list / remove
        +-- get_latest (ACTIVE only)
```

Future phases may connect policy versions to decision and enforcement flows:

```
GovernancePolicyVersion
        |
        v
GovernanceDecision
        |
        v
GovernanceAction
```

Phase 11.8 stops at the registry boundary. No wiring into `GovernanceEvaluator`, `InMemoryGovernanceEngine`, or `GovernanceEnforcer` is performed.

## Components

| Module | Responsibility |
|--------|----------------|
| `versioning/models.py` | `GovernancePolicyVersion` immutable model |
| `versioning/registry.py` | `GovernancePolicyRegistry` protocol |
| `versioning/memory_registry.py` | `InMemoryGovernancePolicyRegistry` (thread-safe) |

## GovernancePolicyVersion

| Field | Description |
|-------|-------------|
| `policy_id` | Stable policy identifier |
| `version` | Semantic version string |
| `name` | Human-readable policy name |
| `description` | Optional description |
| `status` | `DRAFT`, `ACTIVE`, `DEPRECATED`, or `DISABLED` |
| `created_at` | Registration timestamp |
| `metadata` | Optional metadata dictionary |

## Registry Behavior

| Method | Behavior |
|--------|----------|
| `register` | Store or replace a `(policy_id, version)` entry |
| `get` | Return one version by policy id and version |
| `get_latest` | Return highest semantic **ACTIVE** version, or `None` |
| `list_versions` | Return all versions sorted by semantic version |
| `remove` | Delete one version entry |

`get_latest` ignores `DRAFT`, `DEPRECATED`, and `DISABLED` versions. When multiple active versions exist, the highest semantic version wins (e.g. `1.0.10` > `1.0.9`).

## Boundary Rules

The registry **must not**:

- Evaluate policies
- Enforce policies
- Modify governance decisions
- Call `PolicyEngine` or `PermissionEvaluator`
- Integrate with `AgentRuntime` or `AgentExecutionPipeline`

Storage is in-process only via `threading.Lock`. No database, Redis, Kafka, or external services are introduced.

## Usage

```python
from app.runtime.governance import (
    GovernancePolicyVersion,
    InMemoryGovernancePolicyRegistry,
)

registry = InMemoryGovernancePolicyRegistry()
registry.register(
    GovernancePolicyVersion(
        policy_id="runtime.execution",
        version="1.0.0",
        name="Execution Governance Baseline",
        status="ACTIVE",
    )
)

latest = registry.get_latest("runtime.execution")
```

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_policy_versioning.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_policy_versioning.py -q
pytest backend/tests/unit/runtime/ -q
```

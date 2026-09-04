# Runtime Enforcement Pipeline Foundation (Phase 12.6)

## Overview

Phase 12.6 introduces a **runtime enforcement pipeline** that evaluates governance gateway results and produces normalized enforcement outcomes for future runtime integration.

This phase defines the enforcement pipeline model and evaluation bridge only. No runtime execution behavior is changed.

## Purpose

The decision gateway produces `GovernanceGateResult` records. The enforcement pipeline evaluates these gate outcomes and returns `EnforcementResult` records suitable for downstream runtime orchestration.

The pipeline prepares governance for future enforcement integration without modifying existing runtime execution paths.

## Architecture Position

```
EnforcementRequest
        |
        v
RuntimeEnforcementPipeline
        |
        v
EnforcementResult
        |
        v
(Future runtime enforcement integration)
```

## Components

| Module | Responsibility |
|--------|----------------|
| `governance/enforcement_pipeline/models.py` | `EnforcementRequest`, `EnforcementResult` |
| `governance/enforcement_pipeline/pipeline.py` | `RuntimeEnforcementPipeline` protocol |
| `governance/enforcement_pipeline/memory_pipeline.py` | `InMemoryRuntimeEnforcementPipeline` |

## EnforcementRequest

Immutable enforcement pipeline evaluation request:

| Field | Description |
|-------|-------------|
| `execution_id` | Execution identifier |
| `gate_result` | Gateway outcome to evaluate |
| `context` | Additional evaluation context dictionary |
| `metadata` | Additional request metadata |

## EnforcementResult

Immutable enforcement pipeline evaluation result:

| Field | Description |
|-------|-------------|
| `enforcement_id` | Unique enforcement result identifier |
| `execution_id` | Execution identifier |
| `status` | Enforcement outcome status |
| `reason` | Human-readable explanation |
| `timestamp` | Enforcement evaluation timestamp |
| `metadata` | Additional result metadata |

### Enforcement Statuses

| Status | Description |
|--------|-------------|
| `ALLOW` | Execution may proceed |
| `WARN` | Execution may proceed with warning |
| `BLOCK` | Execution should be blocked |
| `PENDING_APPROVAL` | Approval required before proceeding |

## Status Mapping

`InMemoryRuntimeEnforcementPipeline` maps gateway results as follows:

| Gate Status | Enforcement Status |
|-------------|-------------------|
| `ALLOW` | `ALLOW` |
| `WARN` | `WARN` |
| `BLOCK` | `BLOCK` |
| `REQUIRE_APPROVAL` | `PENDING_APPROVAL` |

## RuntimeEnforcementPipeline Protocol

```python
class RuntimeEnforcementPipeline(Protocol):
    def evaluate(self, request: EnforcementRequest) -> EnforcementResult:
        ...
```

Implementations evaluate gateway results and return enforcement results without modifying runtime execution.

## InMemoryRuntimeEnforcementPipeline

Thread-safe in-memory implementation:

- Records evaluated enforcement results
- Supports enable/disable via `enabled` flag
- When disabled, returns `ALLOW` enforcement results without blocking
- Provides `list_results()` and `clear()` for observation and testing

## Boundary Rules

This phase **must not**:

- Modify `AgentRuntime` execution flow
- Modify `AgentExecutionPipeline` control flow
- Modify `ToolExecutionEngine` behavior
- Modify `ExecutionContext`
- Modify `PolicyEngine` or `PermissionEvaluator` logic
- Introduce database, Redis, Kafka, API, or external services

Existing runtime behavior remains backward compatible.

## Usage

```python
from app.runtime.governance.enforcement_pipeline import (
    EnforcementRequest,
    InMemoryRuntimeEnforcementPipeline,
)

pipeline = InMemoryRuntimeEnforcementPipeline()
result = pipeline.evaluate(enforcement_request)
```

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_enforcement_pipeline.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_enforcement_pipeline.py -q
pytest backend/tests/unit/runtime/ -q
```

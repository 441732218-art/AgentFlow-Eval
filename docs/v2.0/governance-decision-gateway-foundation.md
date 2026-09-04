# Governance Decision Gateway Foundation (Phase 12.5)

## Overview

Phase 12.5 introduces a **runtime governance decision gateway** that evaluates governance control outcomes and produces normalized gate results for future runtime enforcement integration.

This phase defines the gateway model and evaluation bridge only. No runtime execution behavior is changed.

## Purpose

The control layer produces `GovernanceControlDecision` records. The decision gateway evaluates these control outcomes and returns `GovernanceGateResult` records suitable for downstream runtime orchestration.

The gateway prepares governance for future enforcement integration without modifying existing runtime execution paths.

## Architecture Position

```
GovernanceGateRequest
        |
        v
GovernanceDecisionGateway
        |
        v
GovernanceGateResult
        |
        v
(Future runtime enforcement integration)
```

## Components

| Module | Responsibility |
|--------|----------------|
| `governance/gateway/models.py` | `GovernanceGateRequest`, `GovernanceGateResult` |
| `governance/gateway/gateway.py` | `GovernanceDecisionGateway` protocol |
| `governance/gateway/memory_gateway.py` | `InMemoryGovernanceDecisionGateway` |

## GovernanceGateRequest

Immutable gateway evaluation request:

| Field | Description |
|-------|-------------|
| `execution_id` | Execution identifier |
| `agent_id` | Agent identifier |
| `tool_name` | Tool being evaluated |
| `decision_id` | Source governance decision identifier |
| `control_decision` | Control outcome to evaluate |
| `metadata` | Additional request metadata |

## GovernanceGateResult

Immutable gateway evaluation result:

| Field | Description |
|-------|-------------|
| `gate_id` | Unique gate result identifier |
| `execution_id` | Execution identifier |
| `status` | Gateway outcome status |
| `reason` | Human-readable explanation |
| `timestamp` | Gateway evaluation timestamp |
| `metadata` | Additional result metadata |

### Gate Statuses

| Status | Description |
|--------|-------------|
| `ALLOW` | Execution may proceed |
| `WARN` | Execution may proceed with warning |
| `REQUIRE_APPROVAL` | Approval required before proceeding |
| `BLOCK` | Execution should be blocked |

## Status Mapping

`InMemoryGovernanceDecisionGateway` maps control decisions as follows:

| Control Status | Gate Status |
|----------------|-------------|
| `ALLOW` | `ALLOW` |
| `WARN` | `WARN` |
| `BLOCK` | `BLOCK` |
| `REQUIRE_APPROVAL` | `REQUIRE_APPROVAL` |

## GovernanceDecisionGateway Protocol

```python
class GovernanceDecisionGateway(Protocol):
    def evaluate(self, request: GovernanceGateRequest) -> GovernanceGateResult:
        ...
```

Implementations evaluate control outcomes and return gate results without modifying runtime execution.

## InMemoryGovernanceDecisionGateway

Thread-safe in-memory implementation:

- Records evaluated gate results
- Supports enable/disable via `enabled` flag
- When disabled, returns `ALLOW` gate results without blocking
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
from app.runtime.governance.gateway import (
    GovernanceGateRequest,
    InMemoryGovernanceDecisionGateway,
)

gateway = InMemoryGovernanceDecisionGateway()
result = gateway.evaluate(gate_request)
```

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_gateway.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_gateway.py -q
pytest backend/tests/unit/runtime/ -q
```

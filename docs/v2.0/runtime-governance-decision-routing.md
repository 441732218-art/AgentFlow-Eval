# Runtime Governance Decision Routing Foundation (Phase 12.9)

## Overview

Phase 12.9 introduces a **standalone governance decision routing layer** that converts normalized governance outcomes into routing decisions.

The router decides which path an execution should follow without executing runtime actions, calling tools, or invoking the policy engine.

## Purpose

Prior governance phases produce layered outcomes:

```
GovernanceDecision
        |
        v
GovernanceControlDecision
        |
        v
EnforcementResult
        |
        v
RuntimeBindingResult
        |
        v
PolicyBindingResult
        |
        v
GovernanceDecisionRouter
        |
        +------------+
        |            |
        v            v
   ALLOW path   BLOCK / APPROVAL path
```

The routing layer normalizes these outcomes into a single routing abstraction for future runtime integration.

## Architecture Position

```
GovernanceRouteRequest
        |
        v
GovernanceDecisionRouter.route()
        |
        v
GovernanceRouteResult
        |
        v
(Future runtime orchestration integration)
```

## Components

| Module | Responsibility |
|--------|----------------|
| `governance/routing/models.py` | `GovernanceRouteRequest`, `GovernanceRouteResult` |
| `governance/routing/router.py` | `GovernanceDecisionRouter` protocol |
| `governance/routing/memory_router.py` | `InMemoryGovernanceDecisionRouter` |

## GovernanceRouteRequest

Normalized governance decision input:

| Field | Description |
|-------|-------------|
| `execution_id` | Execution identifier |
| `decision_status` | Governance decision status |
| `enforcement_status` | Optional enforcement status |
| `policy_id` | Optional policy identifier |
| `metadata` | Additional routing metadata |

## GovernanceRouteResult

Immutable routing decision:

| Field | Description |
|-------|-------------|
| `route_id` | Unique route result identifier |
| `execution_id` | Execution identifier |
| `route_type` | Routing path type |
| `action` | Recommended routing action |
| `approval_required` | Whether approval is required |
| `blocked` | Whether the route indicates blocking |
| `reason` | Human-readable explanation |
| `metadata` | Additional result metadata |

### Route Types

| Route Type | Description |
|------------|-------------|
| `ALLOW` | Continue execution |
| `WARNING` | Continue with warning |
| `APPROVAL` | Wait for approval |
| `BLOCK` | Block execution |
| `UNKNOWN` | Unsupported input status |

## Routing Rules

| Input | Route Type | Action | Approval Required | Blocked |
|-------|------------|--------|-------------------|---------|
| `decision_status="ALLOW"` | `ALLOW` | `CONTINUE` | No | No |
| `decision_status="WARN"` | `WARNING` | `CONTINUE_WITH_WARNING` | No | No |
| `decision_status="REQUIRE_APPROVAL"` | `APPROVAL` | `WAIT_APPROVAL` | Yes | No |
| `decision_status="DENY"` | `BLOCK` | `BLOCK` | No | Yes |
| `enforcement_status="BLOCK"` | `BLOCK` | `BLOCK` | No | Yes |
| Unknown status | `UNKNOWN` | `NO_ACTION` | No | No |

Enforcement block status takes precedence over allow/warn decision statuses.

## GovernanceDecisionRouter Protocol

```python
class GovernanceDecisionRouter(Protocol):
    def route(self, request: GovernanceRouteRequest) -> GovernanceRouteResult:
        ...
```

The router only decides routes. It does not execute actions or modify runtime behavior.

## InMemoryGovernanceDecisionRouter

Thread-safe in-memory implementation:

- Records routing history
- Supports `route()`, `get_route()`, `list_routes()`, and `clear()`
- Disabled mode returns `ALLOW` / `CONTINUE` without blocking
- No external dependencies

## Assembly Placeholder

`RuntimeAssembly` includes optional:

- `governance_decision_router=None`

Default assembly behavior is unchanged. Future phases may wire the router through assembly profiles.

## Responsibility Boundary

This phase **must not**:

- Integrate runtime execution blocking
- Modify `AgentRuntime` execution behavior
- Modify `AgentExecutionPipeline` control flow
- Modify `ToolExecutionEngine` behavior
- Modify `PolicyEngine` or `PermissionEvaluator` logic
- Call runtime, tools, or external services

Existing runtime behavior remains backward compatible.

## Future Integration Point

Future phases may connect:

- Governance lifecycle outcomes into `GovernanceRouteRequest`
- Routed outcomes into runtime orchestration or approval workflows
- Assembly profile flags to enable routing during production assembly

## Testing

Unit tests live in `backend/tests/unit/runtime/test_governance_decision_routing.py`.

Run:

```bash
pytest backend/tests/unit/runtime/test_governance_decision_routing.py -q
pytest backend/tests/unit/runtime/ -q
```

## Usage

```python
from app.runtime.governance.routing import (
    GovernanceRouteRequest,
    InMemoryGovernanceDecisionRouter,
)

router = InMemoryGovernanceDecisionRouter()
result = router.route(
    GovernanceRouteRequest(
        execution_id="exec-1",
        decision_status="WARN",
    )
)
```

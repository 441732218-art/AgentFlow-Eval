# Role-Based Policy Engine

## Summary

Added an optional `RoleBasedPolicyEngine` (`backend/app/runtime/policy/role_based_engine.py`) that implements the existing `PolicyEngine` protocol. It compares caller roles from `ExecutionContext.metadata` against a tool's `permission_scope` (passed via `ToolDefinition.metadata["permission_scope"]` by `PermissionEvaluator`).

Evaluation order:

1. `blocked_tools` deny list (takes precedence over role checks)
2. Empty `permission_scope` → allow (backward compatible)
3. Non-empty `permission_scope` → allow when caller role intersects the scope; otherwise deny

`InMemoryPolicyEngine` is unchanged. This is an opt-in alternative, not a replacement of default runtime behavior.

## Tests

| File | Purpose |
|------|---------|
| `backend/tests/unit/runtime/test_role_based_policy_engine.py` | Unit tests for allow/deny, empty scope, blocked-tools precedence, and `PermissionEvaluator` integration |
| `backend/tests/unit/runtime/test_registry_bridge_experiment.py` | Experimental bridge probe; non-sales deny case updated to use `RoleBasedPolicyEngine` |

Last run:

```
pytest backend/tests/unit/runtime/ -q
→ 673 passed, 1 warning
```

## Open Question: Role Source Not Confirmed

There is no established convention in `backend/app/` for how caller roles are written into `ExecutionContext.metadata`. The engine currently reads provisional keys `metadata["roles"]` (preferred) and `metadata["role"]` (fallback). These are **not** aligned with `app.core.rbac`. How HTTP or other production entry points populate roles remains undecided and must be resolved before this engine is wired into the HTTP production path.

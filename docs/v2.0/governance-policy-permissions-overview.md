# Governance, Policy, and Permissions Overview

Cross-cutting reference for Runtime v2 tool governance components introduced in Phases 9.8�?0.14. This document is derived from the current code under `backend/app/runtime/`.

## Components

| Component | Module | Phase |
|-----------|--------|-------|
| `PolicyEngine` / `InMemoryPolicyEngine` | `policy/engine.py` | 9.8 |
| `RuntimeGovernanceLifecycle` | `governance/lifecycle.py` | 9.9 |
| `ToolCapability` | `tool_registry/models.py` | 10.12 |
| `PermissionEvaluator` | `permissions/evaluator.py` | 10.13 |
| `ToolInvocationGuard` | `invocation/guard.py` | 10.14 |

Related docs: [policy-enforcement-foundation.md](./policy-enforcement-foundation.md), [governance-integration.md](./governance-integration.md).

---

## 1. PolicyEngine default behavior

### Protocol and implementation

`PolicyEngine` is a Protocol with a single method:

```python
def evaluate(context, tool_definition) -> PolicyDecision
```

The default concrete implementation is `InMemoryPolicyEngine` (`policy/engine.py`).

### Default: allow; blocked list: deny

Behavior in `InMemoryPolicyEngine.evaluate()`:

1. Call `evaluate_blocked_tool(tool_name, blocked_tools=..., policy_name=...)`.
2. If the tool name is in `blocked_tools`, return `PolicyDecision(allowed=False, ...)`.
3. Otherwise return `allow_decision(self._policy_name)` �?`allowed=True`.

The statement **“default allow, blocked list deny�?* is **accurate** for `InMemoryPolicyEngine`.

### Where `blocked_tools` is configured

Configured only via the constructor:

```python
InMemoryPolicyEngine(blocked_tools: list[str] | None = None, policy_name: str = "in_memory")
```

Internally: `self._blocked_tools = frozenset(blocked_tools or [])`.

There is **no** environment variable, settings file, or runtime hot-reload for the blocked list in the current codebase.

### Current production default: empty blocked list

`create_production_runtime()` (`bootstrap/factory.py`) builds:

```python
policy_engine = InMemoryPolicyEngine()
```

No `blocked_tools` argument �?**empty frozenset** �?all tools pass `InMemoryPolicyEngine` unless blocked elsewhere (capability registry, permission binding, etc.).

### Fail-open when evaluation throws

Both `ToolExecutionEngine._evaluate_policy()` and `RuntimeGovernanceLifecycle.evaluate_policy()` catch exceptions from `policy_engine.evaluate()`, log at debug, and return `allow_decision("policy_fallback_allow")`.

If `context.policy_engine is None`, they return `allow_decision("default_allow")` without calling an engine.

---

## 2. What callers receive when policy denies execution

Denial surfaces as **exceptions**, not return values. Which exception depends on the code path.

### Path A �?`ToolInvocationGuard` (Phase 10.14)

When `ToolExecutionEngine.invocation_guard` is set and `authorize()` returns `allowed=False`:

- Event: `tool.invocation.denied` (`RuntimeEventType.TOOL_INVOCATION_DENIED`)
- Exception: **`ToolInvocationDeniedError(tool_name, reason)`** (`invocation/errors.py`)

This path runs **before** governance lifecycle or legacy policy evaluation inside the engine.

### Path B �?`RuntimeGovernanceLifecycle.run_tool_execution()` (Phase 9.9)

When `use_governance_lifecycle(context)` is true and lifecycle policy denies:

- Events: `tool.started` (already recorded), then `tool.policy.denied`
- Exception: **`PolicyDeniedError(decision, tool_name)`** (`policy/models.py`)

### Path C �?Legacy engine policy (no governance lifecycle)

When governance lifecycle is not active and the invocation guard did not already handle policy (`guard_handled_policy` is false):

- Event: `tool.policy.denied`
- Exception: **`PolicyDeniedError`**

Note: if `invocation_guard` is set **and** `permission_evaluator` is wired, `handles_policy_evaluation` is true, so the engine **skips** its own `_evaluate_policy()` call (policy was already evaluated inside the guard).

### Path D �?`AgentRuntime._validate_tool_permissions()` (pre-pipeline, Phase 10.13)

When `AgentRuntime` is constructed with `permission_evaluator` and `tool_registry`, before the agent pipeline runs:

- Event: `tool.permission.denied`
- Exception: **`PolicyDeniedError`**

### Propagation to API layer

| Entry point | Behavior on denial |
|-------------|-------------------|
| **`RuntimeService` �?`AgentExecutor`** (HTTP `/runtime/execute`) | `AgentExecutor.execute()` wraps the pipeline in `try/except Exception` and returns `ExecutionResult(status="FAILED", error=str(exc))`. **Exceptions are not re-raised.** HTTP handler returns **200** with `{"status": "FAILED", "error": "<message>", ...}`. |
| **`AgentRuntime.execute()`** (agent service layer) | No broad catch around pipeline execution for tool-policy errors during steps; step failures are converted to `AgentExecutionResult` with `status="FAILED"` and `metadata["error_message"]`. Pre-pipeline `PolicyDeniedError` from `_validate_tool_permissions` **propagates** to the direct caller. |
| **`execute_tool_via_engine()`** (pipeline tool step) | Re-raises the exception after recording `tool.failed` when governance lifecycle is **not** active. When governance lifecycle **is** active, lifecycle records events and raises; outer `tool_step` does not add a second catch. |

**`ENABLE_RUNTIME_V2`** only gates whether the Runtime HTTP API is enabled (503 when false). It does **not** change which exception type is raised or how denials are handled.

### Production wiring note

Default production assembly (`service/tooling_bootstrap.py` �?`create_tool_execution_engine()`) does **not** attach `ToolInvocationGuard` to `ToolExecutionEngine`. Invocation-guard denials occur only when callers explicitly wire a guard (as in unit tests).

---

## 3. RuntimeGovernanceLifecycle hooks and pipeline integration

### `execution_started(context, task)`

Defined in `governance/lifecycle.py`. Publishes `execution.started`.

**Current codebase: this method is never called.** A repository-wide search shows no call sites outside its definition. Agent pipeline startup uses `agent/lifecycle.start_session()` which publishes `agent.started`, not `execution.started`.

### `before_tool_execution(context, tool_definition)`

Called from **`RuntimeGovernanceLifecycle.run_tool_execution()`** at the start of governed tool execution. Publishes `tool.started` and returns a monotonic start timestamp.

**Pipeline stage:** inside `ToolExecutionEngine.execute()` �?`run_tool_execution()`, which is reached from `pipeline/tool_step.execute_tool_via_engine()` when `use_governance_lifecycle(execution_context)` is true (`context.governance_lifecycle is not None`).

When governance lifecycle is **not** active, `tool_step.py` publishes `tool.started` itself before calling `engine.execute()`.

### `run_tool_execution(...)`

Called from **`ToolExecutionEngine.execute()`** when `use_governance_lifecycle(context)` is true.

Orchestrates:

1. `before_tool_execution`
2. `evaluate_policy` �?on deny: `on_policy_denied` + raise `PolicyDeniedError`
3. `adapter.execute(...)`
4. On adapter exception: `after_tool_failure` + re-raise
5. On success: `after_tool_success`

**Pipeline stage:** same tool-step path as above; not invoked at agent prepare/plan boundaries.

### Do lifecycle exceptions fail the whole execution?

**Yes**, when they propagate uncaught:

- **`PolicyDeniedError`** from `run_tool_execution`: propagates out of `ToolExecutionEngine.execute()` �?`execute_tool_via_engine()` �?plan step �?`ExecutionController.execute_step()` catches it, returns `StepControlOutcome(success=False, stop_plan=True)` �?`SequentialExecutionStrategy` returns `ExecutionStrategyResult(status="FAILED")` �?`AgentExecutionPipeline` returns `AgentExecutionResult(status="FAILED")`.
- **Adapter exceptions**: `after_tool_failure` runs, then the exception is re-raised and follows the same step-failure path.
- **`execution_started`**: N/A (unused).

`RuntimeGovernanceLifecycle` methods other than `run_tool_execution` only record events and do not raise on their own in the current implementation.

---

## 4. PermissionEvaluator and unbound tools

### Evaluation flow (`permissions/evaluator.py`)

1. If `not tool_capability.enabled` �?deny (`policy_name="tool_capability"`).
2. Look up `binding = self._bindings.get(tool_capability.tool_name)`.
3. If no explicit binding �?**`binding = binding_from_capability(tool_capability)`** (`permissions/binding.py`), which builds `ToolPermissionBinding.permissions` from `tool_capability.permission_scope`.
4. If `binding.permissions` is non-empty **and** `tool_capability.permission_scope` is empty �?deny (`policy_name="tool_permission_binding"`, reason `"Missing required permissions for {tool_name}"`).
5. Otherwise build a synthetic `ToolDefinition` (with metadata carrying permission info) and call **`self._policy_engine.evaluate(context, tool_definition)`**.

### Default when there is no explicit `ToolPermissionBinding`

There is **no** separate registry of bindings required for every tool. Missing entries in `PermissionEvaluator._bindings` fall back to `binding_from_capability()`.

| Situation | Default |
|-----------|---------|
| No explicit binding, empty `permission_scope`, capability enabled | **Allow** (via `PolicyEngine`, typically `InMemoryPolicyEngine` allow) |
| No explicit binding, non-empty `permission_scope` | **Allow** if `PolicyEngine` allows (binding permissions mirror scope) |
| Explicit binding with permissions, but capability `permission_scope` is empty | **Deny** (step 4 above) |
| Capability disabled | **Deny** (step 1) |

The default-allow behavior for unbound tools is defined implicitly in `evaluate_tool_access()` steps 3�?: absence of an explicit binding does **not** deny; only the explicit-binding/empty-scope mismatch rule denies before policy evaluation.

### `ToolInvocationGuard` without `PermissionEvaluator`

If `permission_evaluator is None`, `authorize()` returns `allow_decision("invocation_guard")` after capability registry checks (tool must exist and be enabled). No `PolicyEngine` call in the guard on that path.

---

## 5. Full tool call order (with interrupt points)

Default production omits the invocation guard; the diagram shows the **fully wired** path when all optional components are attached.

```
ToolExecutionEngine.execute(tool_definition, arguments, context)
�?
├─ [INTERRUPT] TypeError �?invalid tool_definition type
├─ [INTERRUPT] UnknownExecutorTypeError �?no adapter for executor_type
�?
├─ (optional) ToolInvocationGuard.authorize()
�?  ├─ resolve_tool_capability(tool_registry, tool_name)
�?  �?  ├─ [INTERRUPT �?ToolInvocationDeniedError] ToolNotFoundError
�?  �?  └─ [INTERRUPT �?ToolInvocationDeniedError] ToolDisabledError
�?  ├─ if permission_evaluator is None �?allow (skip policy here)
�?  └─ PermissionEvaluator.evaluate_tool_access(context, capability)
�?      ├─ [INTERRUPT �?ToolInvocationDeniedError] disabled capability
�?      ├─ [INTERRUPT �?ToolInvocationDeniedError] binding/scope mismatch
�?      └─ PolicyEngine.evaluate(context, synthetic ToolDefinition)
�?          └─ [INTERRUPT �?ToolInvocationDeniedError] allowed=False
�?
├─ if not guard_decision.allowed
�?  ├─ publish tool.invocation.denied
�?  └─ [INTERRUPT] raise ToolInvocationDeniedError
�?
├─ if use_governance_lifecycle(context):  # context.governance_lifecycle is not None
�?  └─ RuntimeGovernanceLifecycle.run_tool_execution(...)
�?      ├─ before_tool_execution �?tool.started event
�?      ├─ evaluate_policy �?PolicyEngine.evaluate(...)
�?      �?  └─ if denied: on_policy_denied �?[INTERRUPT] PolicyDeniedError
�?      ├─ adapter.execute(tool_definition, arguments, execution_context=context)
�?      �?  └─ [INTERRUPT] adapter/provider exception (after tool.failed event)
�?      ├─ after_tool_success �?tool.completed event
�?      └─ return ToolExecutionResult
�?
└─ else (legacy path)
    ├─ if not guard_handled_policy: PolicyEngine.evaluate via _evaluate_policy()
    �?  └─ if denied: tool.policy.denied �?[INTERRUPT] PolicyDeniedError
    ├─ adapter.execute(...)
    �?  └─ [INTERRUPT] adapter exception (no lifecycle after_tool_failure)
    └─ return ToolExecutionResult
```

### Upstream (before `ToolExecutionEngine.execute`)

When using **`AgentRuntime`** with `permission_evaluator` + `tool_registry`:

```
AgentRuntime.execute()
├─ _validate_tool_capabilities() �?ToolNotFoundError / ToolDisabledError propagate
├─ _validate_tool_permissions() for each agent tool
�?  └─ [INTERRUPT] PolicyDeniedError + tool.permission.denied event
└─ AgentExecutionPipeline.run() �?... �?execute_tool_via_engine() �?ToolExecutionEngine.execute()
```

### Who can interrupt (summary)

| Layer | Mechanism | Typical exception |
|-------|-----------|-------------------|
| Capability registry | Missing/disabled tool | `ToolInvocationDeniedError` (guard) or registry errors (agent pre-check) |
| Permission binding | Scope/binding mismatch | `ToolInvocationDeniedError` or `PolicyDeniedError` (agent pre-check) |
| Policy engine | Blocked tool / custom deny | `ToolInvocationDeniedError` or `PolicyDeniedError` |
| Governance lifecycle | Policy deny after tool.started | `PolicyDeniedError` |
| Adapter / provider | Execution failure | Original exception (e.g. `ValueError`) |

---

## 6. Global switches

There is **no single switch** that disables the entire governance/policy/permission stack and restores completely unchecked tool execution across all entry points.

Existing partial controls:

| Control | Location | Effect |
|---------|----------|--------|
| **`ENABLE_RUNTIME_V2`** | `app/config.py`, default `False` | HTTP Runtime API returns **503** when false. Does not disable in-process policy logic. |
| **`RuntimeConfig.enable_governance`** | `bootstrap/config.py`, default `True` | When `False`: `create_production_runtime()` sets `governance_lifecycle=None`; `create_execution_context()` sets `policy_engine=None` on `ExecutionContext`. Legacy engine path skips policy when `policy_engine` is None. |
| **`ToolExecutionEngine(invocation_guard=None)`** | Default in production factories | No invocation guard; no capability/permission evaluation at engine entry. |
| **`AgentRuntime(permission_evaluator=None)`** | Default | Skips `_validate_tool_permissions()` pre-check. |
| **`PermissionEvaluator` not passed to guard** | Guard constructor | Guard allows after registry resolution without calling `PolicyEngine`. |

**Not present:** an `ENABLE_RUNTIME_V2`-style flag that turns off all permission checks while keeping the Runtime API enabled. Production HTTP path today uses `AgentExecutor` without `invocation_guard`; policy/governance apply only when `ExecutionContext` is wired with `policy_engine` / `governance_lifecycle` (e.g. via `create_execution_context(create_production_runtime())`) and the tool step runs through that context.

---

## Wiring reference (current defaults)

```python
# bootstrap/factory.py
policy_engine = InMemoryPolicyEngine()          # blocked_tools=[]
enable_governance = True                         # RuntimeConfig default
governance_lifecycle = RuntimeGovernanceLifecycle() if enable_governance else None
tool_execution_engine = create_tool_execution_engine(...)  # invocation_guard=None

# service/tooling_bootstrap.py �?HTTP production path
engine = create_tool_execution_engine(handler_registry=...)  # no guard, no PermissionEvaluator
```

To exercise the full stack (guard �?permission �?policy �?lifecycle), callers must explicitly construct `ToolInvocationGuard`, `PermissionEvaluator`, and attach them to `ToolExecutionEngine`, and provide an `ExecutionContext` with `governance_lifecycle` and `policy_engine` as tests do in `test_tool_invocation_guard.py` and `test_governance_flow.py`.

---

## 已知架构缺口（供未来 Phase 参考）

1. 当前治理系统存在三条独立拒绝路径�?

- ToolInvocationDeniedError（ToolInvocationGuard 路径�?
- PolicyDeniedError（Governance / ToolExecutionEngine 路径�?
- PolicyDeniedError（AgentRuntime 预检路径�?

目前三条路径行为不完全统一�?
未来如果强化 Runtime Governance，需要先统一拒绝模型�?
事件命名以及错误传播策略�?

2. 当前生产 HTTP 执行路径�?

/runtime/execute

尚未挂载 ToolInvocationGuard�?

因此�?

Capability Registry�?
Permission Binding�?
Policy Evaluation

当前主要�?Runtime 内部调用链和测试路径生效�?
尚未成为所有生�?Tool Invocation 的统一入口�?

未来 Application 系统接入 Runtime 前，
需要明确是否启用生产路径治理，以及默认策略�?

3. 当前 PermissionEvaluator 默认行为�?

未配置显�?Permission Binding 时：

- 根据 ToolCapability.permission_scope 自动生成 binding
- 继续进入 PolicyEngine
- 默认允许（fail-open�?

该策略适合当前 Runtime Kernel 建设阶段�?

在企业生产环境中，需要重新评估：

- 是否默认 deny
- 是否要求显式 permission declaration
- 是否根据 tenant / user / organization context 动态授�?
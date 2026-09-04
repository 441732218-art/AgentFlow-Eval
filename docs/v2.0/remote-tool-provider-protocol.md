# Remote Tool Provider Protocol (Phase 8.2.3)

**Project:** AgentFlow Intelligence v2.0  
**Phase:** 8.2.3 â€?Remote Tool Executor Adapter + Tool Provider Protocol Skeleton  
**Date:** 2026-08-31

---

## 1. Runtime Boundary

```text
Runtime
  |
  | ToolDefinition (metadata)
  |
  v
ToolExecutionEngine
  |
  v
RemoteToolExecutorAdapter
  |
  | ToolProviderRequest / ToolProviderResponse
  |
  v
RemoteToolClient (transport abstraction)
  |
  v
External System (Provider implements ToolProviderProtocol)
```

Runtime owns **contract, routing, validation, and error mapping**.  
External systems own **business logic, authentication, and vendor APIs**.

---

## 2. Responsibilities

### Runtime

| Responsibility | Owner |
|----------------|-------|
| Tool capability metadata (`ToolDefinition`) | Runtime |
| Execution lifecycle routing | `ToolExecutionEngine` |
| Provider request/response contract | `ToolProviderProtocol` |
| Response validation | `RemoteToolExecutorAdapter` |
| External error â†?Runtime error mapping | `errors.py` |

### Provider (External)

| Responsibility | Owner |
|----------------|-------|
| Business implementation | External provider |
| Authentication / credentials | External provider |
| Vendor HTTP/API calls | External provider |
| Retry / timeout policy (future) | External provider or transport layer |

---

## 3. Protocol Contract

**File:** `backend/app/runtime/tools/provider.py`

### ToolProviderRequest

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | Capability name from `ToolDefinition.name` |
| `arguments` | `dict` | Invocation arguments |
| `metadata` | `dict` | Copied from `ToolDefinition.metadata` |

### ToolProviderResponse

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether execution succeeded |
| `output` | `Any` | Result payload when `success=True` |
| `error` | `str \| None` | Error message when `success=False` |
| `metadata` | `dict` | Provider-supplied metadata |

### ToolProviderProtocol

```python
class ToolProviderProtocol(ABC):
    def invoke(self, request: ToolProviderRequest) -> ToolProviderResponse: ...
```

Not bound to CRM, HTTP libraries, or specific vendors.

---

## 4. Adapter Architecture

```text
ToolDefinition (executor_type="remote")
        |
        v
RemoteToolExecutorAdapter
        |
        | build ToolProviderRequest
        v
RemoteToolClient.send(request)
        |
        v
ToolProviderResponse
        |
        | validate + map errors
        v
output (or ToolExecutionError)
```

**Files:**

| File | Purpose |
|------|---------|
| `remote_adapter.py` | `RemoteToolExecutorAdapter` |
| `remote_client.py` | `RemoteToolClient`, `InMemoryRemoteClient` |
| `provider.py` | Protocol dataclasses + ABC |
| `errors.py` | Unified Runtime error boundary |

---

## 5. Error Boundary

| External / transport | Runtime exception |
|---------------------|-------------------|
| Generic failure | `RemoteProviderError` |
| Timeout (future transport) | `RemoteTimeoutError` |
| Invalid response shape | `RemoteResponseValidationError` |
| Base type | `ToolExecutionError` |

Runtime **does not propagate** raw third-party exceptions. Unknown exceptions are wrapped in `RemoteProviderError` with `cause` preserved.

---

## 6. Registry Integration

```python
engine = create_tool_execution_engine(remote_client=client)
```

Registers:

```text
"local"  â†?LocalToolExecutorAdapter
"remote" â†?RemoteToolExecutorAdapter
```

`create_default_tool_execution_engine()` remains **local-only** for backward compatibility.

---

## 7. Not Included (Phase 8.2.3)

This phase does **not** implement:

- CRM adapter
- Email provider
- Search provider
- OAuth / API key management
- HTTP client (`requests`, `httpx`)
- Schema validation against `input_schema`
- Retry / timeout transport
- Observability hooks

These belong to **Phase 8.3+**.

---

## 8. Phase 8.3 Preparation

Phase 8.3 will add concrete remote provider implementation specs:

| Topic | Phase 8.3 scope |
|-------|-----------------|
| Authentication | API keys, OAuth headers |
| Schema validation | `input_schema` enforcement |
| Timeout | Transport deadline |
| Retry | Resilience policy |
| Observability | Trace propagation to provider |

Current skeleton keeps Runtime Core clean:

```text
ToolDefinition
        |
ToolExecutionEngine
        |
+----------------+
|                |
Local Adapter    Remote Adapter
|                |
Python           Provider Protocol
Callable         External Service
```

---

## Appendix: Files Added (Phase 8.2.3)

| File | Purpose |
|------|---------|
| `tools/errors.py` | Runtime tool execution errors |
| `tools/provider.py` | Tool Provider Protocol contract |
| `tools/remote_client.py` | `RemoteToolClient`, `InMemoryRemoteClient` |
| `tools/remote_adapter.py` | `RemoteToolExecutorAdapter` |
| `tools/factory.py` | `create_tool_execution_engine()` extended |
| `tests/unit/runtime/test_remote_tool_adapter.py` | 9 unit tests |

**Not modified:** API, core, executor, service, memory, tracing.
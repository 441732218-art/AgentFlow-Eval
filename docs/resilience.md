# 弹性与高可用：重试 / 熔断 / 超时 / 降级

AgentFlow-Eval 对外部 LLM / HTTP 调用统一使用 `app.core.resilience` 保护，避免级联故障。

## 能力一览

| 能力 | 默认 | 实现 |
|------|------|------|
| 重试 | 最多 **3** 次，指数退避 1s～10s | **tenacity** |
| 熔断 | 连续失败 **5** 次打开，**60s** 后半开探测 | 进程内 `CircuitBreaker`（async 安全） |
| 超时 | 单次调用 **30s** | `asyncio.wait_for` / 线程超时 |
| 降级 | LLM 失败 → **规则引擎**评分 | Judge `mode=rule_only` + `degraded=true` |

## 配置（环境变量）

| 变量 | 默认 | 说明 |
|------|------|------|
| `LLM_RETRY_ENABLED` | `true` | 是否启用重试 |
| `LLM_MAX_RETRIES` | `3` | 最大尝试次数（含首次） |
| `LLM_RETRY_MIN_WAIT_SEC` | `1.0` | 退避下限 |
| `LLM_RETRY_MAX_WAIT_SEC` | `10.0` | 退避上限 |
| `LLM_CALL_TIMEOUT_SEC` | `30.0` | 单次 API 超时 |
| `CIRCUIT_ENABLED` | `true` | 是否启用熔断 |
| `CIRCUIT_FAILURE_THRESHOLD` | `5` | 打开熔断的连续失败次数 |
| `CIRCUIT_RECOVERY_TIMEOUT_SEC` | `60.0` | 打开后到半开探测的等待秒数 |

与 Judge 总超时区分：`JUDGE_TIMEOUT_SEC` 包裹整次 `evaluate()`；`LLM_CALL_TIMEOUT_SEC` 约束单次 LLM HTTP 调用。

## 调用链

```
protected_call_async(fn)
  ├─ CircuitBreaker  (OPEN → 拒绝 / 走 fallback)
  ├─ tenacity retry  (指数退避，最多 3 次)
  │    └─ with_timeout(fn)  (默认 30s)
  └─ 失败 → fallback（可选）
```

### Judge 降级

1. 始终先跑规则预评分（`_pre_score`）
2. 有 API Key 时走 `protected_call_async` 调用 LLM 精化
3. 重试耗尽 / 熔断打开 / 超时 / 其它错误 → 返回规则分  
   - `mode = "rule_only"`  
   - `degraded = true`  
   - reason 追加 `[degraded: ...]`

### OpenAI ReAct Runner

每次 `chat.completions.create` 经 `protected_call_async` 保护；迭代内异常仍按原有 step 错误路径处理。

## 代码用法

```python
from app.core.resilience import (
    ResiliencePolicy,
    default_llm_policy,
    protected_call_async,
    CircuitOpenError,
)

policy = default_llm_policy("my_service")

async def call_api():
    ...

async def fallback():
    return {"mode": "rule_only"}

result = await protected_call_async(
    call_api,
    policy=policy,
    fallback=fallback,
)
```

同步：`protected_call(...)`。

仅重试 / 仅超时：

```python
from app.core.resilience import retry_async, with_timeout

await retry_async(fn, max_attempts=3, min_wait=1, max_wait=10)
await with_timeout(coro, timeout_sec=30, name="op")
```

熔断器：

```python
from app.core.resilience import get_breaker, CircuitOpenError

breaker = get_breaker("llm_judge:gpt-4o-mini")
try:
    await breaker.call_async(my_async_fn)
except CircuitOpenError:
    ...
```

## Prometheus 指标

| 指标 | 标签 | 含义 |
|------|------|------|
| `agentflow_resilience_retries_total` | `name` | 重试次数 |
| `agentflow_resilience_circuit_calls_total` | `name`, `result` | 熔断视角成功/失败 |
| `agentflow_resilience_circuit_state_transitions_total` | `name`, `state` | 状态观察（closed/open/half_open） |
| `agentflow_resilience_fallbacks_total` | `name`, `reason` | 降级次数（error/timeout/circuit_open） |
| `agentflow_resilience_timeouts_total` | `name` | 超时次数 |

`name` 示例：`llm_judge:gpt-4o-mini`、`openai_react:gpt-4o-mini`。

## 状态机（熔断）

```
CLOSED ──(连续失败 ≥ threshold)──► OPEN
OPEN   ──(recovery_timeout 到期)──► HALF_OPEN
HALF_OPEN ──(探测成功)──► CLOSED
HALF_OPEN ──(探测失败)──► OPEN
```

## 测试

```bash
cd backend
pytest tests/unit/test_resilience.py -v
```

覆盖：重试成功/耗尽、熔断打开/半开恢复、超时、fallback、Judge 规则降级。

## 注意

- 熔断状态为 **进程内** 内存；多 worker 时各自独立（与 Prometheus 进程内指标一致）。
- 可重试异常默认含：`TimeoutError`、`ConnectionError`、`OSError`、`httpx` 传输错误、OpenAI 超时/限流类异常。
- 生产建议：熔断阈值与下游 SLA 对齐；超时略小于上游网关超时，避免双超时抖动。

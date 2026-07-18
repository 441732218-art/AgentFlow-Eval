# AgentFlow Observability Logging System  
## 日志系统审计报告 + 架构设计（第 1 轮）

| 属性 | 内容 |
|------|------|
| **项目** | AgentFlow-Eval → AgentFlow Intelligence |
| **文档类型** | 审计报告 + 目标架构（**本轮无代码改动**） |
| **范围** | `backend/app` 日志 / 中间件 / Celery / Runner / Judge / 可观测 / 存储 |
| **日期** | 2026-07-18 |
| **结论摘要** | 已有 TraceID、Prometheus、审计表与文件日志骨架，**不足以支撑企业级 Agent 可观测**；Dashboard / Diagnosis 主要依赖业务表聚合，**几乎不读结构化日志** |

---

## 0. 执行说明

本轮仅做：

1. 全量审计现有实现  
2. 差距分析（相对 Dashboard / Trace / Diagnosis / Token / 性能）  
3. 目标架构与事件体系设计  
4. 分阶段实施计划（对应你建议的第 2～4 轮）  

**明确不做：** 改代码、加表、改 API。

---

## 1. 现状地图

### 1.1 相关模块一览

| 模块 | 路径 | 职责 | 日志成熟度 |
|------|------|------|------------|
| 日志配置 | `app/utils/logger.py` | RotatingFile + 可选 structlog | **B-** 半成品 |
| 配置 | `app/config.py` | `LOG_LEVEL/FILE/FORMAT` | **B** |
| Request ID | `app/core/middleware.py` | X-Request-ID、access 文本日志 | **B** |
| Trace context | `app/core/observability/tracing.py` | contextvars TraceID | **A-** |
| Prometheus | `app/core/observability/metrics.py` | HTTP/任务/Judge/Token 计数 | **A-**（指标≠日志） |
| KPI / 时序 | `business_kpis.py` / `timeseries.py` | ORM 聚合给 Dashboard | **B+**（业务库） |
| 慢任务 | `slow_tasks.py` | 内存环 + DB 表 | **B** |
| 审计 | `app/core/audit.py` + `AuditLog` 表 | 变更操作落库 | **B+**（非运行日志） |
| 任务事件 | `app/core/events.py` | Redis/本地 task_status 推 WS | **B**（活动流） |
| Celery | `app/core/celery_app/tasks.py` | 评测编排 | **C+** 字符串日志 |
| OpenAI Runner | `agent_runner/openai_runner.py` | ReAct 循环 | **C** 仅异常 |
| Http Runner | `http_runner.py` | 外部 Agent | **C** 仅错误 |
| Tool sandbox | `tool_sandbox.py` | 工具执行 | **C** 失败 warning |
| LLM Judge | `judge_engine/llm_judge.py` | 评分 | **C** 失败 warning |
| 异常响应 | `utils/exceptions.py` + `main.py` handlers | 统一 error JSON | **B** 无 error_id |
| 成本 | `utils/cost.py` | Token→USD 计算 | **A-**（有函数，未强制记日志） |

### 1.2 调用方式统计（关键结论）

| 模式 | 使用情况 |
|------|----------|
| `logging.getLogger(__name__)` | **全项目主流** |
| `structlog.get_logger` | **未发现任何业务调用** |
| 事件名（`task.finished`） | **几乎没有**；多为中文/英文句子 |
| JSON 字段化 kwargs | **无**；`%s` 格式化字符串 |

→ 即使 `LOG_FORMAT=json`，structlog 已配置，**业务代码仍不产出可查询的结构化事件流**。

---

## 2. 逐层审计发现

### 2.1 Logger 配置（`utils/logger.py`）

**已有：**

- 控制台 + 滚动文件（10MB × 30）  
- 静音 httpx/openai/celery 等噪声库  
- structlog processors：contextvars、TimeStamper、JSON/Console  

**问题：**

| # | 问题 | 影响 |
|---|------|------|
| L1 | 默认 `LOG_FORMAT=text` | 生产难采集 |
| L2 | **stdlib Formatter 始终是纯文本** | 文件日志无法被 ELK/Loki 直接解析；structlog 与 stdlib 双轨 |
| L3 | 无统一 `get_logger()` 封装 | 无法强制 service/env/trace 绑定 |
| L4 | 无敏感字段过滤器 | 风险：prompt/key 可能进日志 |
| L5 | 无 `service` / `environment` 字段注入 | 多实例难区分 |
| L6 | 未与 `get_trace_id()` 自动合并到每条 stdlib 日志 | TraceID 仅 middleware 字符串拼接 |

### 2.2 FastAPI 中间件

**已有（`RequestIDMiddleware`）：**

- 生成/透传 `X-Request-ID` / `X-Trace-ID`  
- `set_trace_id(request_id)`  
- 日志：`METHOD path -> status [duration] request_id=...`  

**缺失：**

| # | 缺失 | 影响 |
|---|------|------|
| M1 | 无 `client_ip`、`user_agent`、`actor` | 安全与租户分析弱 |
| M2 | 异常路径可能不记完整 access log | 视 Starlette 异常传播而定 |
| M3 | 无 `error_id` 生成与响应回写 | 用户报障无法对账 |
| M4 | 4xx/5xx 未分级为 `http.request.failed` | 告警规则难写 |
| M5 | 未采样 / 未排除 health 高频噪声策略文档化 | 生产日志量 |

`MetricsMiddleware` 有 Prometheus 计数，**不写业务日志**（正确分工，但日志侧空白）。

### 2.3 全局异常处理（`main.py`）

**已有：** `AgentFlowError` + 兜底 `Exception` → `error_response(..., request_id=)`  

**缺失：**

- 无稳定 `error_id`（UUID）  
- 未保证 exception 日志带 `trace_id` + `path` + `actor`  
- 未统一 `event=system.error`  

### 2.4 Celery 任务（`tasks.py`）

**已有：**

- `run_full_evaluation` 恢复 `_trace_id`  
- 文本：`[Task %s] Full evaluation started trace_id=%s`  
- Suite / Judge start/complete/fail 的 info/exception  
- Prometheus observe_* 指标  

**缺失 / 不足：**

| # | 问题 | 影响 |
|---|------|------|
| C1 | 无标准 lifecycle 事件枚举 | 无法统计 `evaluation.failed` 率自日志 |
| C2 | `retry_count` / `worker_name` / `hostname` 未记 | 运维盲区 |
| C3 | duration 有 perf_counter，**未稳定输出到结构化字段** | 日志侧无法做 p95 |
| C4 | suite 日志只有 suite_id，**不总是绑定 task_id** 在同一条日志 | 关联成本高 |
| C5 | 成功路径字段不齐：model、runner、tokens、cost | Token 成本分析断链 |

### 2.5 Agent Runner

**OpenAI ReAct（`openai_runner.py`）：**

- 仅有 iteration 失败、整体失败 `logger.exception`  
- **无** `agent.started` / step 级 thought/action/tool/observation/final  
- Token 可能写入 Trace 模型，**未同步 event 日志**  
- 无法从日志重建 Agent 执行过程（只能查 DB Trace）

**Http Runner：** 超时 / HTTP / unexpected 三类 warning，无 request body 脱敏策略、无 latency 字段。

**Tool sandbox：** 失败 `Tool %s failed`，无 started/completed、无 latency、无 success 布尔、input/output 未结构化（且若打印有敏感风险）。

### 2.6 LLM / Judge

- Judge 仅在 refine 失败时 warning  
- **无** `llm.started` / `llm.completed`  
- **无** provider/model/temperature/input_tokens/output_tokens/latency_ms/cost  
- `calculate_cost` 存在但**未强制挂钩日志与计量事件**

### 2.7 数据库

- 启动时 `Tables initialized` / SQLite backfill info  
- **无** 连接池失败、事务回滚、慢 SQL 的结构化日志  
- ORM echo 未作为可控观测通道设计  

### 2.8 存储与查询

| 能力 | 现状 |
|------|------|
| 文件日志 | `logs/agentflow_eval.log` 文本滚动 |
| `agent_logs` 表 | **不存在** |
| AuditLog | 仅变更审计，非执行轨迹 |
| Trace / MetricScore | 业务结果表，非通用日志事件 |
| `GET /api/v1/logs` | **不存在** |
| `GET /api/v1/logs/statistics` | **不存在** |

### 2.9 与前端 Intelligence 的数据鸿沟

| 前端能力 | 当前数据源 | 日志贡献 |
|----------|------------|----------|
| Dashboard Health / series | ORM 聚合 + timeseries | **0** |
| Trace Explorer | `traces` 表 | 日志不驱动 |
| Diagnosis | 启发式扫 Trace steps | 无 `agent.loop.detected` 等日志事件 |
| Analytics | KPI + traces scores | 无日志统计 API |
| Monitoring 日志流 | 前端本地拼装 + slow tasks | **非真实后端日志流** |

**关键判断：** 现在的 Dashboard 是「业务表 BI」，不是「可观测日志平台」。要达到企业级，日志必须成为**可查询的一等公民**，与 Trace 表互补。

---

## 3. 问题归类总表

### 3.1 缺失日志

1. Agent 步骤级（THOUGHT/ACTION/TOOL/OBSERVATION/FINAL）  
2. LLM 全生命周期 + token/cost  
3. Tool started/completed 成功路径  
4. Evaluation lifecycle 标准事件  
5. HTTP 失败 / error_id  
6. DB 故障类  
7. 诊断类：`agent.loop.detected` / `token.anomaly` / `tool.timeout` / `prompt.performance.degraded`  

### 3.2 字段不足

每条日志普遍缺少完整集合：

`timestamp, level, service, environment, request_id, trace_id, task_id, agent_id, step_*, model, tokens, latency_ms, cost, event, actor`

### 3.3 无法追踪的问题

| 场景 | 为何难查 |
|------|----------|
| 用户报「评测很慢」 | 无逐步 latency 日志；仅有任务总时长/Prometheus |
| 「某工具偶发失败」 | 无 tool.completed 成功基线，难算失败率 |
| 「Token 暴涨」 | 无逐步 token 日志；仅有 trace 总量 |
| 「跨 worker 请求」 | TraceID 已有透传，但日志文本难检索 |
| 「对接客服 error_id」 | 响应无 error_id |

### 3.4 无法支撑 Dashboard 的数据

- 错误数量时间序列（日志侧）  
- 按 event 聚合失败率  
- LLM cost 日趋势（若未写 cost 到日志/表）  
- 实时日志流（Monitoring 页）  

---

## 4. 目标架构设计

### 4.1 名称

**AgentFlow Observability Logging System (AOLS) v1.0**

### 4.2 逻辑架构

```
┌─────────────────────────────────────────────────────────────┐
│  FastAPI / Celery / AgentRunner / Judge / Tools             │
└───────────────────────────┬─────────────────────────────────┘
                            │ emit(event, **fields)
┌───────────────────────────▼─────────────────────────────────┐
│  Observability Facade  (app/logging/)                       │
│  - get_logger() / bind_context()                            │
│  - Event enum                                               │
│  - Redactor (API keys, Authorization, password)             │
└───────┬─────────────────────────────┬───────────────────────┘
        │                             │
        ▼                             ▼
┌───────────────┐             ┌───────────────────┐
│ structlog     │             │ Optional sink     │
│ JSON → stdout │             │ agent_logs (DB)   │
│ + file JSON   │             │ async batch write │
└───────┬───────┘             └─────────┬─────────┘
        │                               │
        ▼                               ▼
   Loki/ELK/文件采集              GET /api/v1/logs
   Prometheus(已有)               GET /api/v1/logs/statistics
                                        │
                                        ▼
                              Dashboard / Diagnosis / Monitoring
```

### 4.3 设计原则

1. **Event-first**：`logger.info("evaluation.completed", task_id=...)`  
2. **Context 自动绑定**：middleware/celery 入口 `bind(trace_id, request_id, actor, service, env)`  
3. **双写可选**：默认 JSON 文件；`LOG_DB_SINK=true` 时写 `agent_logs`  
4. **不破坏现有 API**：新接口加法；旧接口行为不变  
5. **与 Trace 表分工**：Trace = 评测结果真相；Logs = 运行过程与运维信号  
6. **与 Prometheus 分工**：指标用于告警/SLI；日志用于溯源/诊断  

### 4.4 统一日志信封（Envelope）

```json
{
  "timestamp": "2026-07-18T10:00:00.000Z",
  "level": "info",
  "event": "llm.completed",
  "service": "agentflow-api",
  "environment": "prod",
  "request_id": "…",
  "trace_id": "…",
  "actor": "user@tenant",
  "agent_context": {
    "agent_id": "react-default",
    "agent_version": "1.0.0",
    "execution_id": "…",
    "task_id": "…"
  },
  "step_context": {
    "step_id": "…",
    "step_type": "TOOL_CALL",
    "step_index": 2
  },
  "payload": { }
}
```

### 4.5 Event 枚举（目标 `app/logging/events.py`）

| 类别 | Events |
|------|--------|
| Agent | `AGENT_STARTED`, `AGENT_STEP_COMPLETED`, `AGENT_FAILED`, `AGENT_LOOP_DETECTED` |
| LLM | `LLM_STARTED`, `LLM_COMPLETED`, `LLM_FAILED` |
| Tool | `TOOL_STARTED`, `TOOL_COMPLETED`, `TOOL_FAILED`, `TOOL_TIMEOUT` |
| Evaluation | `EVALUATION_CREATED`, `EVALUATION_STARTED`, `EVALUATION_RUNNING`, `EVALUATION_COMPLETED`, `EVALUATION_FAILED` |
| HTTP | `HTTP_REQUEST`, `HTTP_REQUEST_FAILED` |
| System | `SYSTEM_ERROR`, `DB_ERROR` |
| Analytics | `TOKEN_ANOMALY_DETECTED`, `PROMPT_PERFORMANCE_DEGRADED` |

对外日志 `event` 字段使用 **点分小写**：`evaluation.completed`（枚举值映射）。

### 4.6 Agent step_type

强制枚举：

`THOUGHT | ACTION | TOOL_CALL | OBSERVATION | FINAL_ANSWER | JUDGE`

与现有 Trace step 类型映射：

| 现有 step | 日志 step_type |
|-----------|----------------|
| thought | THOUGHT |
| action / tool | TOOL_CALL 或 ACTION |
| observation | OBSERVATION |
| final_answer | FINAL_ANSWER |
| judge phase | JUDGE |

### 4.7 LLM / Tool 强制字段

**LLM：**  
`provider, model, prompt_version, temperature, input_tokens, output_tokens, total_tokens, latency_ms, cost`

**Tool：**  
`tool_name, input(redacted), output(redacted/summary), latency_ms, success`

### 4.8 存储：`agent_logs`（建议）

```text
id            PK (uuid/str)
trace_id      indexed
task_id       indexed, nullable
level         indexed
event         indexed
service
payload       JSON  -- 完整信封或扩展字段
created_at    indexed
```

索引建议：`(created_at DESC)`, `(task_id, created_at)`, `(trace_id)`, `(event, created_at)`, `(level, created_at)`。

**保留策略：** 默认 14～30 天（配置项 `LOG_DB_RETENTION_DAYS`）；文件日志仍按滚动策略。

### 4.9 API（目标，第 4 轮）

```
GET /api/v1/logs
  ?page&page_size&level&event&task_id&trace_id&from&to

GET /api/v1/logs/statistics
  ?days=7
  → error_count, agent_failure_rate, token_trend[], latency_trend[]
```

权限：复用 `EVALUATION_READ` 或新增 `logs:read`；强制 tenancy 过滤。

### 4.10 安全

Redactor 规则（配置+默认）：

- Header: `Authorization`, `X-API-Key`  
- Body/kwargs keys: `password`, `api_key`, `openai_api_key`, `secret`, `token`  
- 可选：prompt 截断 `LOG_PROMPT_MAX_CHARS=500`  
- Tool output 默认 hash/截断，debug 级才全量  

### 4.11 故障诊断映射

| 诊断类型 | 日志事件 | 触发启发（实现时） |
|----------|----------|-------------------|
| Agent Loop | `agent.loop.detected` | 相同 tool+input ≥ N |
| Token 异常 | `token.anomaly.detected` | 单步/总量超阈值 |
| Tool 超时 | `tool.timeout` | latency > threshold 或 timeout 异常 |
| Prompt 退化 | `prompt.performance.degraded` | 同 prompt_version 分数滑动下降 |

Diagnosis 引擎第 2 阶段可读：**(1) Trace 表 (2) agent_logs 事件**，提高置信度。

---

## 5. 目标目录结构（第 2 轮起落地）

```
backend/app/logging/          # 新建包（避免与 stdlib logging 混淆可用 observability/logging）
  __init__.py                 # get_logger, setup
  config.py                   # 与 settings 桥接
  events.py                   # Event 枚举
  context.py                  # bind/clear agent/step context
  processors.py               # redactor, add service/env/trace
  sinks/
    db_sink.py                # agent_logs 批量写入
  middleware.py               # 可选：增强 access log 辅助

# 或放在
backend/app/core/observability/logging/
```

**建议包名：** `app.obs_logging` 或 `app.core.observability.structlog_ext`，避免 `import logging` 阴影。  
文档内称 **AOLS**；代码目录推荐：

```
backend/app/core/observability/aols/
  events.py
  logger.py
  context.py
  redaction.py
  sinks/db.py
```

迁移时 `setup_logging()` 仍从 `app.utils.logger` 调用，内部转调 AOLS。

---

## 6. 与现有组件兼容策略

| 现有 | 策略 |
|------|------|
| `tracing.get_trace_id` | 保留；processor 自动注入 |
| Prometheus metrics | 保留；关键路径可 double-emit |
| AuditLog | 保留；不与 agent_logs 合并 |
| task events (WS) | 保留；可选从 evaluation.* 事件派生 |
| Trace ORM | 保留为评测结果；步骤日志为补充 |
| Dashboard series | 短期仍 ORM；statistics API 后可 dual-source |

**兼容红线：** 不改现有 REST 语义；新路由加法；日志失败不得拖垮主流程（sink best-effort）。

---

## 7. 风险与约束

| 风险 | 缓解 |
|------|------|
| 日志量暴涨（逐步日志） | 可配置 `LOG_AGENT_STEPS=true`；生产采样 |
| 写库拖慢评测 | 异步队列/批量 insert；默认关 DB sink |
| 敏感 prompt 泄露 | Redactor + 截断 + 默认不记全文 |
| Celery 多进程 context | 任务入口强制 bind；fork 后 re-bind |
| SQLite 写锁 | lite 模式优先文件 JSON，DB sink 限流 |

---

## 8. 成功标准（v1.0 Definition of Done）

1. 默认生产可切 `LOG_FORMAT=json`，每条含 `event/trace_id/service/environment`  
2. 一次完整评测可在日志中串起：`evaluation.*` → `agent.*` → `llm.*` → `tool.*` → `judge`  
3. `GET /api/v1/logs` 可按 task_id/trace_id 查到步骤  
4. `GET /api/v1/logs/statistics` 能为 Dashboard 提供 error/token/latency 趋势之一  
5. 单测覆盖：redactor、event 枚举、context bind、middleware 字段  
6. 现有 unit/e2e 不回归  

---

## 9. 分轮实施计划（严格对齐你的顺序）

### 第 1 轮（本轮）✅

- 审计报告 + 架构设计  
- **无代码**

### 第 2 轮（下一轮执行）

**范围：** structlog 硬化 + TraceID 全自动注入 + FastAPI Middleware 增强  

| 交付 | 说明 |
|------|------|
| AOLS logger 工厂 | `get_logger`，强制 JSON 字段 |
| Processors | service/env/trace_id/request_id/redactor |
| Middleware | client_ip、latency、status、error_id、跳过 /health 可配置 |
| Exception handler | error_id + `system.error` |
| 单测 | redactor、middleware 字段快照 |

**不做：** Runner/Celery 细粒度步骤、DB 表、/logs API。

### 第 3 轮

**范围：** Agent Runner + LLM + Tool + Celery lifecycle  

- evaluation.* / agent.* / llm.* / tool.*  
- step_context 绑定  
- cost 计算挂钩  
- loop/timeout 初步检测 emit  

### 第 4 轮

**范围：** Dashboard 日志接口 + 数据分析  

- alembic：`agent_logs`  
- sink 可选写入  
- `GET /logs` + `GET /logs/statistics`  
- （可选）Monitoring 页接真实 API  
- Diagnosis 可消费 anomaly 事件  

---

## 10. 第 2 轮预估改动面（仅清单，不实施）

| 文件 | 动作 |
|------|------|
| `app/utils/logger.py` | 重构为 AOLS 入口 |
| `app/core/observability/aols/*` | **新建** |
| `app/core/middleware.py` | 增强 access log |
| `app/main.py` | exception + error_id |
| `app/config.py` | LOG_SERVICE_NAME, ENV, redaction flags |
| `tests/unit/test_aols_*.py` | **新建** |

---

## 11. 审计结论（一句话）

> AgentFlow 已具备 **TraceID 透传、Prometheus、审计表、文件日志与 ORM 看板** 的「观测拼图」，但缺少 **统一结构化事件日志、Agent/LLM/Tool 全链路事件、可查询日志存储与 API**；  
> 当前 Intelligence UI **无法** 以企业级日志为数据基础，必须按第 2→3→4 轮补齐 AOLS。

---

## 12. 下一轮指令建议

请直接回复：

**「执行第 2 轮：structlog + Trace ID + FastAPI Middleware」**

收到后将只改第 2 轮范围，并按你的输出模板给出：修改文件列表 / 原因 / 代码 / 测试命令与结果 / 第 3 轮计划。

---

*文档路径：`docs/observability-logging-audit.md`*  
*状态：第 1 轮完成 · 无业务代码变更*

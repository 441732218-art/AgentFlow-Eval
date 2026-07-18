# 业务可观测：KPI · 慢任务 · 错误拓扑

在现有 Prometheus `/metrics` 与审计日志之上，增加 **业务只读 API**。

## API

```
GET /api/v1/observability/kpis?days=7
GET /api/v1/observability/slow-tasks?limit=50
GET /api/v1/observability/error-topology?days=7
```

### KPIs 字段

- `tasks_total` / `by_status`
- `success_rate`（completed / terminal）
- `avg_metric_score`
- `total_tokens` / `avg_trace_latency_ms`
- `error_topology`（failed / timeout / cancelled / running）

### 慢任务（内存 + 持久化）

`observe_suite_run` / `observe_judge` 当 `duration > SLOW_TASK_THRESHOLD_SEC`（默认 30s）时：

1. 写入进程内环形缓冲（200 条）
2. 异步落库 `slow_task_events`（migration `011`）

```
GET /api/v1/observability/slow-tasks?source=auto|db|memory
```

### TraceID 全链路

```
HTTP X-Request-ID
  → RequestIDMiddleware / contextvars
  → 响应 X-Trace-ID
  → enqueue kwargs _trace_id
  → Celery run_full_evaluation / suite / judge 恢复 contextvar
  → audit.detail.trace_id + usage_records.trace_id + slow_task_events.trace_id
```

抽检：同一 `trace_id` 可在 audit、usage、slow_task_events、worker 日志中检索。

### 错误拓扑（Prometheus）

| 指标 | 说明 |
|------|------|
| `agentflow_stage_errors_total{stage,status}` | agent / judge / pipeline 错误计数 |
| `agentflow_slow_tasks_total{stage}` | 慢任务采样次数 |

Grafana 面板示例：`docs/grafana-agentflow.json`（Import 到 Grafana，数据源选 Prometheus）。

## 配置

```env
OBSERVABILITY_KPI_ENABLED=true
SLOW_TASK_THRESHOLD_SEC=30
```

```bash
cd backend && alembic upgrade head   # includes 011_slow_task_events
```

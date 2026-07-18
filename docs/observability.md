# 可观测性：Prometheus 指标

AgentFlow-Eval 内置 Prometheus 指标采集，用于监控 API 流量、评测流水线耗时与成功率。

## 端点

| 路径 | 说明 |
|------|------|
| `GET /metrics` | Prometheus text exposition（**无需 API Key**） |

关闭指标：

```bash
METRICS_ENABLED=false
```

关闭后 `/metrics` 返回 `404`。

## 抓取配置示例

```yaml
# prometheus.yml
scrape_configs:
  - job_name: agentflow-eval
    metrics_path: /metrics
    scrape_interval: 15s
    static_configs:
      - targets: ["localhost:8000"]
```

Docker Compose 中可增加：

```yaml
prometheus:
  image: prom/prometheus:v2.54.0
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"
```

## 指标一览

前缀：`agentflow_`

### HTTP 层

| 指标 | 类型 | 标签 | 说明 |
|------|------|------|------|
| `agentflow_http_requests_total` | Counter | `method`, `path`, `status` | 请求总数 |
| `agentflow_http_request_duration_seconds` | Histogram | `method`, `path`, `status` | 请求延迟 |

路径中的 UUID / 数字 ID 会归一化为 `{id}`，避免高基数。

### 业务层

| 指标 | 类型 | 标签 | 说明 |
|------|------|------|------|
| `agentflow_tasks_created_total` | Counter | `tenant`, `model`, `runner` | 任务创建数 |
| `agentflow_evaluations_total` | Counter | `status`, `tenant`, `model`, `runner` | 完整流水线结束次数 |
| `agentflow_evaluation_duration_seconds` | Histogram | `status`, `runner` | 流水线总耗时 |
| `agentflow_suite_runs_total` | Counter | `status`, `runner` | 单用例 Agent 执行次数 |
| `agentflow_suite_run_duration_seconds` | Histogram | `status`, `runner` | 单用例执行耗时 |
| `agentflow_judge_evaluations_total` | Counter | `mode`, `status` | Judge 次数 |
| `agentflow_judge_duration_seconds` | Histogram | `mode`, `status` | Judge 耗时 |
| `agentflow_tokens_total` | Counter | `stage`, `model`, `runner` | Token 消耗（agent/judge/evaluation） |

### 标签约定

| 标签 | 含义 | 示例 |
|------|------|------|
| `tenant` | 创建者 actor（API Key 映射名） | `alice`, `anonymous` |
| `model` | `agent_config.model` | `gpt-4o-mini` |
| `runner` | `agent_config.runner` | `openai`, `http` |
| `status` | 结果状态 | `completed`, `failed`, `partial`, `success` |
| `mode` | Judge 模式 | `rule_only`, `hybrid` |
| `stage` | Token 阶段 | `agent`, `judge`, `evaluation` |

## 成功率 PromQL 示例

```promql
# 评测成功率（5m）
sum(rate(agentflow_evaluations_total{status="completed"}[5m]))
/
sum(rate(agentflow_evaluations_total[5m]))

# HTTP 5xx 比例
sum(rate(agentflow_http_requests_total{status=~"5.."}[5m]))
/
sum(rate(agentflow_http_requests_total[5m]))

# 流水线 P95 延迟
histogram_quantile(
  0.95,
  sum(rate(agentflow_evaluation_duration_seconds_bucket[5m])) by (le, runner)
)
```

## 代码集成点

| 位置 | 指标 |
|------|------|
| `MetricsMiddleware` | HTTP 计数 / 延迟 |
| `POST /api/v1/tasks` | `tasks_created` |
| `run_single_test_suite` | suite 计数 / 延迟 / tokens |
| `run_judge_evaluation` | judge 计数 / 延迟 / tokens |
| `run_full_evaluation` | evaluation 计数 / 延迟 / tokens |

装饰器（async）：

```python
from app.core.observability.metrics import track_duration

@track_duration("evaluation")
async def my_job() -> dict:
    return {"status": "completed", "total_tokens": 10, "tenant": "ops"}
```

## 多进程注意

Gunicorn 多 worker 时，默认进程内 Registry **不聚合**跨进程计数。生产建议：

1. 单 worker + 多个 uvicorn 进程由外部编排，或
2. 配置 `prometheus_client` multiprocess 模式（`PROMETHEUS_MULTIPROC_DIR`）。

当前默认适用于 **单进程 / Eager 本地开发** 与 Docker 单 replica API。

## 配置项

| 环境变量 | 默认 | 说明 |
|----------|------|------|
| `METRICS_ENABLED` | `true` | 是否启用采集与 `/metrics` |

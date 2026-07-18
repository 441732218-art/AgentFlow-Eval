# 数据库优化（Phase 3）

面向 AgentFlow-Eval 真实模型与热路径查询，在不改动业务语义的前提下提升列表与聚合性能。

> 说明：设计文档中的 `tenant_id` / 宽表 Trace 字段为演进方向；当前实现以  
> `Task.created_by`、`Trace.test_suite_id`、`MetricScore.trace_id` 为准。

## 规模假设

| 表 | 年量级（目标） | 热路径 |
|----|----------------|--------|
| `tasks` | 10万～100万 | 列表（租户 + 归档 + 时间序） |
| `test_suites` | 随任务 | 按 `task_id` 计数 / 加载 |
| `traces` | 100万～1000万 | 按 suite 列表、报告聚合 |
| `metric_scores` | 50万～500万 | 按 `trace_id` 加载评分 |
| `experiments` / `experiment_runs` | 较低 | 按 owner / experiment_id |
| `audit_logs` | 中高 | 按时间 / action 筛选 |

## 索引策略

### 已有（001_initial 等）

- `tasks(created_at)`, `tasks(status)`
- `test_suites(task_id)`
- `traces(test_suite_id)`, `traces(status)`
- `metric_scores(trace_id)`, `metric_scores(metric_name)`
- `experiment_runs(experiment_id)`, `experiment_runs(task_id)`

### 新增（007_performance_indexes + ORM `__table_args__`）

| 索引 | 列 | 服务查询 |
|------|-----|----------|
| `ix_tasks_owner_archived_created` | created_by, is_archived, created_at | `GET /tasks` 默认列表 |
| `ix_tasks_status_created` | status, created_at | 按状态筛选 |
| `ix_tasks_created_by` | created_by | 租户隔离 |
| `ix_tasks_celery_task_id` | celery_task_id | 取消 / 追踪 |
| `ix_tasks_is_archived` | is_archived | 归档过滤 |
| `ix_traces_suite_created` | test_suite_id, created_at | suite 下轨迹列表 |
| `ix_traces_created_at` | created_at | 时间范围扫描 |
| `ix_metric_scores_trace_metric` | trace_id, metric_name | 评分维度查找 |
| `ix_metric_scores_human_reviewed` | is_human_reviewed | 人工复核筛选 |
| `ix_experiments_owner_created` | created_by, created_at | 实验列表 |
| `ix_experiments_base_task_id` | base_task_id | 溯源 |
| `ix_audit_logs_*` | created_at / action / resource / actor+time | 审计查询 |

迁移：

```bash
cd backend
alembic upgrade head
# → 007_performance_indexes
```

SQLite 开发库若走 `create_all`，ORM 索引会在新库创建时生效；已有文件库请跑 Alembic。

## 查询优化

### 1. 任务列表 N+1 → 批量 COUNT

**之前**：每条任务一次 `COUNT(test_suites)`（页大小 20 → 21 次查询）。

**现在**：

```python
from app.core.db.queries import batch_suite_counts

counts = await batch_suite_counts(session, [t.id for t in tasks])
# 一次 GROUP BY task_id
```

实现：`app/core/db/queries.py`  
接入：`GET /api/v1/tasks`。

### 2. 实验列表 N+1 → 批量 runs + tasks

`GET /api/v1/experiments` 对当前页实验一次加载全部 `ExperimentRun`，再一次 `Task.id IN (...)` 取状态。

### 3. 报告 / Trace 详情

继续使用 `selectinload` 预取 `metric_scores`，避免懒加载爆炸。

## 连接与 SQLite

| 后端 | 配置 |
|------|------|
| PostgreSQL | `pool_size` / `max_overflow` / `pool_pre_ping` / `pool_recycle=3600` |
| SQLite | `check_same_thread=False`；连接时 `PRAGMA journal_mode=WAL`、`synchronous=NORMAL`、`foreign_keys=ON`、`busy_timeout=5000` |

配置项：`DATABASE_URL`、`DB_POOL_SIZE`、`DB_MAX_OVERFLOW`、`DB_ECHO`。

## 建议的后续演进（未在本阶段实现）

1. **分区**：PostgreSQL 上 `traces` / `metric_scores` 按月 RANGE 分区（`created_at`）。
2. **归档表**：冷数据迁入 `traces_archive`，列表只扫热表。
3. **物化计数**：`tasks.suite_count` 冗余字段 + 触发器 / 应用维护（进一步去掉 COUNT）。
4. **读写分离**：报告类只读走 replica。
5. **JSON 索引**：若常按 `agent_config->>'model'` 筛选，用 PG `jsonb` + GIN。

## 验收自检

```bash
cd backend
alembic upgrade head
pytest tests/unit/test_db_queries.py tests/unit/test_tasks_api.py -q
```

## 相关代码

| 路径 | 说明 |
|------|------|
| `alembic/versions/007_performance_indexes.py` | 索引迁移 |
| `app/models/*.py` | `__table_args__` 索引声明 |
| `app/core/db/queries.py` | 批量 suite_count |
| `app/core/dependencies.py` | 连接池 + SQLite PRAGMA |

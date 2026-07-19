# Benchmark 平台

企业级行业评测集：创建套件 → 导入 JSON/CSV → 调用 **既有 Evaluation Engine** → 排行榜。

## 数据模型

| 表 | 用途 |
|----|------|
| `benchmarks` | 套件元数据 |
| `benchmark_cases` | 用例（query / expected） |
| `benchmark_runs` | 一次运行（绑定 `task_id`） |
| `benchmark_results` | 用例级 accuracy/quality/latency/cost/tokens |

迁移：`015_benchmarks.py`

## API

```
GET    /api/v1/benchmarks
POST   /api/v1/benchmarks
GET    /api/v1/benchmarks/{id}
POST   /api/v1/benchmarks/{id}/import          { format, content }
POST   /api/v1/benchmarks/{id}/import/file     multipart
POST   /api/v1/benchmarks/{id}/run             { label, agent_config, enqueue }
POST   /api/v1/benchmarks/{id}/runs/{run_id}/finalize
GET    /api/v1/benchmarks/{id}/leaderboard
```

权限：`benchmark:read` / `benchmark:create`（兼容 `task:read` / `task:execute`）。

## 运行路径（不改 Pipeline）

1. 从 cases 创建 `Task` + `TestSuite`
2. `get_task_queue().enqueue("run_full_evaluation", task_id)`
3. `finalize` 从 Trace / MetricScore 聚合指标
4. `leaderboard` 按 `label` 排名

## 前端

路由：`/benchmarks`（Evaluate 导航组）

## 导入格式

**JSON**

```json
[
  {"name": "c1", "user_query": "hi", "expected_output": "hello", "expected_tools": []}
]
```

**CSV**

```csv
name,user_query,expected_output,expected_tools,weight
c1,hi,hello,,1
```

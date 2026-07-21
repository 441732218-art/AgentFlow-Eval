# Benchmark 与持续评测（Phase 4）

在现有 **Task / Experiment / Scorecard / Trace** 之上，提供：

1. **Benchmark（评测基准）** — 固定用例 + 版本 + 可选 Scorecard  
2. **手动回归试跑** — 指定 `agent_config`，复用 Evaluation Engine  
3. **基础退化检测** — 当前试跑 vs 基线，给出提升 / 持平 / 下降  

> 本阶段 **不做** 定时调度、复杂告警、多 Benchmark 大盘；不引入第二套执行引擎。

## 概念关系

```
Benchmark (meta: version, scorecard, source_task_id)
  └── BenchmarkCase[]          # 固定用例
  └── BenchmarkRun[]           # 每次试跑
        ├── task_id → Task + TestSuite  # 执行管道
        ├── agent_config               # 本次模型/runner
        ├── summary                    # 聚合指标
        └── BenchmarkResult[]          # 用例级指标 → Trace/MetricScore
```

| 实体 | 说明 |
|------|------|
| **Benchmark** | 评测基准；`meta.version` / `meta.scorecard` / `meta.source_task_id` |
| **BenchmarkRun** | 一次 EvaluationRun；绑定 `task_id`，可追溯到 Task |
| **Comparison** | 纯计算产物（不落库）：`compare_runs(current, baseline)` |

试跑时若 Benchmark 绑定了 scorecard，会注入 `agent_config.scorecard`，与 Phase 3 Judge 路径一致。

## 数据模型

| 表 | 用途 |
|----|------|
| `benchmarks` | 套件元数据（`meta` JSON 存 version/scorecard） |
| `benchmark_cases` | 用例（query / expected） |
| `benchmark_runs` | 一次运行（绑定 `task_id`） |
| `benchmark_results` | 用例级 score / latency / cost / tokens |

迁移：`015_benchmarks.py`（无新表；version/scorecard 走 `meta`）

## API

```
GET    /api/v1/benchmarks
POST   /api/v1/benchmarks
       body: name, description, version?, scorecard?, source_task_id?, cases?
GET    /api/v1/benchmarks/{id}
POST   /api/v1/benchmarks/{id}/import          { format, content }
POST   /api/v1/benchmarks/{id}/import/file     multipart
POST   /api/v1/benchmarks/{id}/run             { label, agent_config, enqueue }
GET    /api/v1/benchmarks/{id}/runs            # 历史试跑（自动 best-effort finalize）
POST   /api/v1/benchmarks/{id}/runs/{run_id}/finalize
POST   /api/v1/benchmarks/{id}/compare
       body: { current_run_id, baseline_run_id?, score_stable_eps? }
GET    /api/v1/benchmarks/{id}/leaderboard
```

### 对比响应要点

```json
{
  "verdict": "improved | stable | regressed | unknown",
  "headline": "整体提升（Δscore=+3.50）；主要提升：answer_correctness (+4.00)",
  "score_delta": 3.5,
  "success_rate_delta": 0.0,
  "score_coverage_delta": 0.0,
  "dimension_deltas": { "tool_accuracy": 1.0, "answer_correctness": 4.0 },
  "top_changes": [{ "dimension": "answer_correctness", "delta": 4.0 }],
  "current": { "run_id": "...", "summary": { ... } },
  "baseline": { "run_id": "...", "summary": { ... } }
}
```

**退化判定（P0）**

- `|Δscore| < score_stable_eps`（默认 1.0）→ `stable`  
- `Δscore > 0` → `improved`  
- `Δscore < 0` → `regressed`  
- 无总分 → `unknown`  
- 附带 top 维度变化作为「主要变化点」

权限：`benchmark:read` / `benchmark:create`（兼容 `task:read` / `task:execute`）。

## 运行路径（不改 Pipeline）

1. 从 cases 创建 `Task` + `TestSuite`（suite.meta 带 `benchmark_case_id`）  
2. `get_task_queue().enqueue("run_full_evaluation", task_id)`  
3. `finalize` 从 Trace / MetricScore 聚合 summary（score、dimension_scores、success_rate、score_coverage）  
4. `compare` 对比两次 summary；`leaderboard` 按 `label` 排名  

## 前端闭环

路由：`/benchmarks`（导航：**持续评测**）

| 区域 | 能力 |
|------|------|
| 列表 | 名称 / 版本 / case 数 |
| 详情 | 版本、Scorecard 绑定、来源 Task、用例表 |
| 触发试跑 | label + runner/model/endpoint |
| 历史试跑 | status / score / 成功率 / 覆盖 / 链到 Task / 刷新 finalize |
| 对比 | 选 current & baseline → Δscore / 维度 / 结论 Tag |

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

## 本地验证路径

```text
1. 创建 Benchmark（手写 cases 或 source_task_id）
2. POST /run 两次（不同 label / model），enqueue=false 时需模拟 Trace 后 finalize
3. GET /runs 查看历史
4. POST /compare 看 verdict 与 dimension_deltas
5. UI：侧栏「持续评测」走通同一路径
```

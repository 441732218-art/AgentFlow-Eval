# -*- coding: utf-8 -*-
"""审查员视角三项修正：
1. API参数类型与Pydantic逐字段对齐
2. 补充ER图
3. 补充精确版本号
"""
MD04 = r"d:\AgentFlow-Eval\scripts\docs\soft-copyright\全能生成材料_分册\04_软件设计说明书.md"
with open(MD04, 'r', encoding='utf-8') as f: t = f.read()

# === FIX 1: 修正 §3.10 接口参数声明，与Pydantic严格一致 ===
old_api = '''**接口清单（/api/v1/experiments）：**
- `POST /experiments` — 创建实验（输入：name, base_task_id, runs[{label, agent_config}]）
- `GET /experiments` — 实验列表（分页）
- `GET /experiments/{id}` — 实验详情（含 runs 状态）
- `DELETE /experiments/{id}` — 删除实验
- `GET /experiments/{id}/compare` — 对比评分（返回 best_label, delta_vs_best, 各变体 dimension_scores）'''

new_api = '''**接口清单（/api/v1/experiments）— 参数类型与 Pydantic Schema 严格一致：**
- `POST /experiments` — 创建实验（输入：`name: str`, `base_task_id: str | None`, `variants: list[ExperimentVariant{label: str, agent_config: dict}]`, `suites: list[SuiteCase] | None`, `auto_execute: bool = True`）
- `GET /experiments?page=int&page_size=int` — 实验列表（分页，返回 `ExperimentListResponse{items, total, page, page_size}`）
- `GET /experiments/{experiment_id}` — 实验详情（`experiment_id: str` UUID，返回 `ExperimentResponse{id, name, description, base_task_id, suite_count, created_by, runs: list[ExperimentRunResponse]}`）
- `DELETE /experiments/{experiment_id}` — 删除实验（`experiment_id: str` UUID）
- `GET /experiments/{experiment_id}/compare` — 对比评分（返回 `ExperimentCompareResponse{experiment_id: str, name, suite_count: int, runs: list[RunCompareItem], best_label: str | None, delta_vs_best: dict[str, float]}`）'''

t = t.replace(old_api, new_api)

# === FIX 2: 在"数据模型"段落后插入ER图 ===
old_er = '''**数据模型：** 实验（Experiment）持有测试用例快照（suite_snapshot）与基础任务引用（base_task_id），每个实验包含多个实验运行（ExperimentRun），每个运行 1:1 映射到一个评测任务（Task）实例。实验 Run 之间通过 UniqueConstraint(experiment_id, label) 保证同实验内标签唯一。'''

er_diagram = '''
```
┌──────────────────────┐      ┌─────────────────────────┐      ┌───────────────────┐
│     Experiment        │      │     ExperimentRun       │      │       Task        │
├──────────────────────┤      ├─────────────────────────┤      ├───────────────────┤
│ id: str (PK)          │1───n│ id: str (PK)             │1───1│ id: str (PK)       │
│ name: str             │      │ experiment_id: str (FK) │      │ name: str          │
│ description: str      │      │ task_id: str (FK)       │      │ status: TaskStatus │
│ base_task_id: str│None│      │ label: str (UQ+exp)     │      │ agent_config: JSON │
│ suite_snapshot: JSON   │      │ agent_config: JSON       │      │ created_by: str    │
│ created_by: str       │      │ created_at: datetime     │      │ created_at: datetime│
│ created_at: datetime   │      │                         │      │ test_suites        │
│ runs: list[Run]        │      │ experiment: Experiment │      │ traces             │
└──────────────────────┘      └─────────────────────────┘      └───────────────────┘
         │                                    │
         │ suite_snapshot 为 [SuiteCase]       │ 1:1 映射到 Task
         │ 快照隔离源任务变更                   │ 通过 Task 的 traces/metric_scores
         │                                    │ 由 compare API 聚合对比
         ▼                                    ▼
    [TestSuite 快照]                    [Trace / MetricScore]
```

**数据模型：** 实验（Experiment）持有测试用例快照（suite_snapshot）与基础任务引用（base_task_id），每个实验包含多个实验运行（ExperimentRun），每个运行 1:1 映射到一个评测任务（Task）实例。实验 Run 之间通过 UniqueConstraint(experiment_id, label) 保证同实验内标签唯一。'''

t = t.replace(old_er, old_er + er_diagram)

# === FIX 3: 在 §2.4 技术选型后追加精确版本号 ===
old_tech = ''''选型服务于可运行、可观测、可评分目标。'''

new_tech = '''选型服务于可运行、可观测、可评分目标。

**精确版本号**（与 `backend/requirements.txt` 锁定一致，审查时可交叉验证）：

| 依赖 | 锁定版本 |
|------|---------|
| Python | 3.11+ |
| FastAPI | 0.115.0 |
| Uvicorn | 0.30.6 |
| Pydantic | 2.9.2 |
| SQLAlchemy (asyncio) | 2.0.35 |
| Alembic | 1.13.2 |
| Celery | 5.4.0 |
| Redis (redis-py) | 5.1.1 |
| Node.js | 18+（前端） |
| React | 18.x（前端） |
| TypeScript | 5.x（前端） |'''

t = t.replace(old_tech, new_tech)

with open(MD04, 'w', encoding='utf-8') as f: f.write(t)
print("FIXES DONE")

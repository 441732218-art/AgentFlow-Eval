# -*- coding: utf-8 -*-
"""
终稿修订全流程：
- 03手册: A/B实验附录 + 术语确认
- 04设计: A/B实验章节 + 替换"总览"
- 02代码: 追加模块K(experiment) + 文件路径注释
"""
import os, re

BASE = r"d:\AgentFlow-Eval\scripts\docs\soft-copyright\全能生成材料_分册"
MD03 = os.path.join(BASE, '03_用户使用手册.md')
MD04 = os.path.join(BASE, '04_软件设计说明书.md')
MD02 = os.path.join(BASE, '02_核心源代码.md')

# ==== 1. 读取真实源码 ====
exp_model = open(r'd:\AgentFlow-Eval\backend\app\models\experiment.py', encoding='utf-8').read()
exp_api = open(r'd:\AgentFlow-Eval\backend\app\api\v1\endpoints\experiments.py', encoding='utf-8').read()

# ==== 2. 修订 03_用户使用手册 ====
with open(MD03, 'r', encoding='utf-8') as f: t3 = f.read()

# 2.1 新增A/B实验附录 (在"9. 注意事项"之后)
ab_sec = '''

## 10. 对比实验（A/B 实验 — 高级功能）

**入口：** 当前版本未在导航栏集成，需通过地址栏 `/experiments` 直接访问。

A/B 对比实验功能用于在相同测试用例（TestSuite）集上运行多组不同配置的 Agent（如不同模型或工具组合），并自动对比各变体的多维指标分（MetricScore），标识最优变体及相对于基线的得分差异。

**主要能力：**
- 创建实验（Experiment）并指定基础评测任务作为用例来源
- 为每个变体（Variant）配置独立的 Agent 参数（模型、温度、工具等）
- 自动执行各变体评测并与基准对比
- 输出对比报告（best_label、delta_vs_best、维度分对比）

> 该功能后端 API 已完整实现（见核心源代码鉴别材料模块 K），前端实验管理界面可通过 `/experiments` 访问。完整集成计划于 V2.0 版本。

![对比实验](ab_experiment.png)

> 图14：A/B 对比实验界面（ab_experiment.png）'''

t3 = t3.rstrip() + '\n' + ab_sec

with open(MD03, 'w', encoding='utf-8') as f: f.write(t3)
print("[03] A/B实验附录已追加")

# ==== 3. 修订 04_软件设计说明书 ====
with open(MD04, 'r', encoding='utf-8') as f: t4 = f.read()

# 3.1 替换"总览"
t4 = t4.replace('总览模块', '驾驶舱模块')
t4 = t4.replace('>总览', '>驾驶舱')

# 3.2 在第四章后追加A/B实验章节
ab_design = '''

### 3.10 对比实验（A/B 实验）服务模块

A/B 对比实验模块提供多变体评测的创建、执行与结果对比能力。在相同测试用例（TestSuite）快照基础上，用户可为每个实验变体（Run）指定独立的 Agent 配置（模型、温度、提示词等），系统并行或串行执行评测后聚合各变体指标分（MetricScore），并自动计算最优变体（best_label）及各变体相对于最优的得分差值（delta_vs_best）。

**数据模型：** 实验（Experiment）持有测试用例快照（suite_snapshot）与基础任务引用（base_task_id），每个实验包含多个实验运行（ExperimentRun），每个运行 1:1 映射到一个评测任务（Task）实例。实验 Run 之间通过 UniqueConstraint(experiment_id, label) 保证同实验内标签唯一。

**接口清单（/api/v1/experiments）：**
- `POST /experiments` — 创建实验（输入：name, base_task_id, runs[{label, agent_config}]）
- `GET /experiments` — 实验列表（分页）
- `GET /experiments/{id}` — 实验详情（含 runs 状态）
- `DELETE /experiments/{id}` — 删除实验
- `GET /experiments/{id}/compare` — 对比评分（返回 best_label, delta_vs_best, 各变体 dimension_scores）

**独创性说明：** 本模块将“同一基准集、多配置对照”的评测范式抽象为领域模型，并通过快照机制隔离实验与源任务变更，保证历史对比的可重复性；对比算法由 pick_best_label / deltas_vs_best 实现，非简单调用第三方统计库，由著作权人李凯昕独立设计实现。

**输入输出规格：** 输入为实验名称、基础任务标识、变体配置列表；输出为 ExperimentResponse（含 id, name, base_task_id, runs, suite_count, created_by）、ExperimentCompareResponse（含 best_label, delta_vs_best, runs[].dimension_scores）。错误时返回标准错误体（BusinessError 或 NotFoundError）。

**与其他模块交互细节：** 创建实验时从 base_task 加载测试用例（TestSuite）并快照；每个 Run 调用评测执行引擎创建并执行独立的评测任务（Task）；对比接口通过 aggregate_task_scores 聚合轨迹中的 MetricScore；审计日志（AuditLog）记录实验创建与删除操作。
'''

# Insert before 第四章
t4 = t4.replace('\n## 第四章 数据库设计思路', ab_design + '\n\n## 第四章 数据库设计思路')

with open(MD04, 'w', encoding='utf-8') as f: f.write(t4)
print("[04] A/B实验章节已插入 + 总览术语已替换")

# ==== 4. 修订 02_核心源代码 ====
with open(MD02, 'r', encoding='utf-8') as f: t2 = f.read()

# 4.1 追加模块K
module_k = '''

---

## 模块 K：A/B 对比实验（app/models/experiment.py）

```python
''' + exp_model.strip() + '''

```

---

## 模块 K（续）：实验 API 路由（app/api/v1/endpoints/experiments.py 摘要）

```python
''' + exp_api.strip() + '''

```

***

（连续完整源程序请以 `scripts/export-soft-copyright.ps1` 导出的前 30 页与后 30 页为准；本材料侧重核心业务逻辑鉴别。）'''

t2 = t2.replace(
    '（连续完整源程序请以 `scripts/export-soft-copyright.ps1` 导出的前 30 页与后 30 页为准；本材料侧重核心业务逻辑鉴别。）',
    module_k
)

# 4.2 更新模块说明
t2 = t2.replace(
    '任务 API、WebSocket 实时推送',
    '任务 API、WebSocket 实时推送、A/B 对比实验'
)

with open(MD02, 'w', encoding='utf-8') as f: f.write(t2)
print("[02] 模块K(experiment)已追加")

print("\n=== 修订完成 ===")

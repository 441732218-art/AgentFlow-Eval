# -*- coding: utf-8 -*-
"""终稿级修订 Part 2b: 5.6~5.13 + 章节编号整理"""
MD = r"d:\AgentFlow-Eval\scripts\docs\soft-copyright\全能生成材料_分册\03_用户使用手册.md"
with open(MD, 'r', encoding='utf-8') as f:
    txt = f.read()

# 5.6 运行监控
txt = txt.replace(
    '### 4.6 执行轨迹与 DAG 可视化\n\n**入口：** 任务详情中的轨迹 / 链路区域。\n\n**交互闭环：**\n\n1. 选择某条执行轨迹（Trace）→ 加载步骤数据。  \n2. 界面展示 ReactFlow DAG 节点（思考 / 工具 / 观察 / 最终答案）。  \n3. 点击节点或查看步骤日志面板 → 展示详细内容、Token 与耗时。  \n4. 评分卡片展示规则分与（如有）LLM 精修后的指标分（MetricScore）。  ',
    '### 5.6 运行监控\n\n'
    '**入口：** 左侧导航 COMMAND 分组「监控」或路由 `/monitoring`。\n\n'
    '运行监控页面提供系统运行时的完整可观测性视图：\n\n'
    '**基础设施状态面板**\n'
    '- **API Gateway** — API 网关健康状态\n'
    '- **Redis Broker** — Redis 消息代理连接状态\n'
    '- **PostgreSQL** — 数据库连接状态\n'
    '- **Celery Workers** — 异步任务 Worker 在线数与忙闲状态\n'
    '- **Queue Depth** — 消息队列深度实时值\n\n'
    '**Fleet Activity（集群活动）** — 各 Worker 节点当前处理的任务状态列表。\n\n'
    '**LIVE LOG STREAM（实时日志流）** — 滚动输出的 Agent 运行日志流，支持按级别（INFO/WARN/ERROR）过滤。\n\n'
    '**SLOW TASKS（慢任务）** — 超过延迟阈值的任务列表，展示任务名称、耗时与所属 Worker。\n\n'
    '![运行监控](monitoring.png)\n\n'
    '> 图7：运行监控界面（monitoring.png）'
)

# 5.7 轨迹回溯
txt = txt.replace(
    '### 4.7 人工复核与重新评判',
    '### 5.7 轨迹回溯（Trace）\n\n'
    '**入口：** 左侧导航 COMMAND 分组「Trace」或路由 `/traces`。\n\n'
    '轨迹回溯页面提供执行过程的完整可视化追溯：\n\n'
    '**视图结构**\n'
    '- **TRACE TREE** — 左侧执行轨迹树，按时间线展示步骤层级\n'
    '- **TRACE DETAIL** — 右侧详情面板，展示当前选中步骤的：\n'
    '  - **Latency** — 步骤耗时\n'
    '  - **Tokens** — Token 消耗量\n'
    '  - **Steps** — 步骤数\n'
    '  - **AVG SCORE** — 平均评分\n\n'
    '**视图切换标签**\n'
    '- **Steps** — 步骤列表视图\n'
    '- **DAG** — ReactFlow 有向无环图视图\n'
    '- **Metrics** — 指标分视图\n\n'
    '**Steps 展开详情** — 点击某一步骤可展开查看：\n'
    '- **Prompt** — 发送给 LLM 的完整提示词\n'
    '- **Input** — 步骤输入数据\n\n'
    '**操作按钮**\n'
    '- **诊断（Diagnosis）** — 转入故障诊断分析\n'
    '- **Judge（评判）** — 触发 LLM 重新评判\n\n'
    '![轨迹回溯](trace.png)\n\n'
    '> 图8：轨迹回溯 — Trace Tree 与 Trace Detail 界面（trace.png）\n\n'
    '> 图9：轨迹回溯 — Steps/DAG/Metrics 视图与步骤展开详情（同一截图已涵盖，trace.png）\n\n'
    '### 5.8 人工复核与重新评判'
)

# 5.10 评测报告
txt = txt.replace(
    '### 4.8 评测报告\n\n**入口：** 导航「报告」或 `/reports`，以及任务侧报告入口。',
    '### 5.10 评测报告\n\n**入口：** 左侧导航 EVALUATE 分组「报告」或路由 `/reports`，以及任务侧报告入口。'
)

# 5.13 设置中心
txt = txt.replace(
    '### 4.9 系统设置\n\n**入口：** 导航「设置」或 `/settings`。\n\n**交互闭环：**\n\n1. 打开设置页 → 加载主题、工作区与鉴权相关提示。  \n2. 切换主题或保存偏好 → 界面即时生效。  \n3. 查看工具沙箱列表或探测结果（如界面提供）。  ',
    '### 5.13 设置中心\n\n'
    '**入口：** 左侧导航 SYSTEM 分组「设置中心」或路由 `/settings`。\n\n'
    '设置中心提供以下配置管理功能：\n\n'
    '**交互闭环：**\n\n'
    '1. 打开设置页 → 加载主题、工作区与鉴权相关配置项。\n'
    '2. 切换主题或保存偏好 → 界面即时生效。\n'
    '3. 查看工具沙箱列表或探测结果（如界面提供）。\n'
    '4. API 密钥管理与外部服务集成配置。'
)

with open(MD, 'w', encoding='utf-8') as f:
    f.write(txt)
print("Part 2b done: 5.6~5.13")

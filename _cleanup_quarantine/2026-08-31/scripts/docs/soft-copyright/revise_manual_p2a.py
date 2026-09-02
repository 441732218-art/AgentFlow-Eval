# -*- coding: utf-8 -*-
"""终稿级修订 Part 2a: 插入系统导航结构 + 5.1~5.5"""
MD = r"d:\AgentFlow-Eval\scripts\docs\soft-copyright\全能生成材料_分册\03_用户使用手册.md"
with open(MD, 'r', encoding='utf-8') as f:
    txt = f.read()

# 插入 4. 系统导航结构 (在3.3之后)
nav = (
    '。\n\n---\n\n## 4. 系统导航结构\n\n'
    '系统采用左-右布局，左侧导航栏按四大功能分组组织：\n\n'
    '**COMMAND（命令与控制）**\n'
    '- **驾驶舱（AI Command Center）** — `/dashboard`\n'
    '- **Trace（轨迹回溯）** — `/traces`\n'
    '- **故障诊断** — `/diagnosis`\n'
    '- **分析（分析中心）** — `/analytics`\n'
    '- **监控（运行监控）** — `/monitoring`\n\n'
    '**EVALUATE（评测）**\n'
    '- **任务（评测任务列表）** — `/tasks`\n'
    '- **创建任务** — `/tasks/create`\n'
    '- **报告** — `/reports`\n\n'
    '**OPERATE（运营）**\n'
    '- **用量计费** — `/billing`\n'
    '- **插件市场** — `/plugins`\n\n'
    '**SYSTEM（系统）**\n'
    '- **设置中心** — `/settings`\n\n'
    '![导航结构图](nav_overview.png)\n\n'
    '> 图2：系统导航结构图（nav_overview.png）\n\n'
    '---\n\n## 5. 功能模块详解\n'
)
txt = txt.replace(
    '注意：正式提交截图时须使用真实业务样式数据，不可保留 Demo/test 水印。\n\n---\n\n## 4. 功能模块详解',
    nav
)

# 5.1 驾驶舱
txt = txt.replace(
    '### 4.1 总览（Dashboard）\n\n**入口：** 左侧导航「总览」或路由 `/`。\n\n**交互闭环：**\n\n1. 点击「总览」菜单 → 加载统计卡片与近期活动区域。  \n2. 系统请求评测任务（Task）列表与状态聚合数据。  \n3. 界面展示任务数量、状态分布及活动通知入口。  ',
    '### 5.1 驾驶舱（AI Command Center）\n\n'
    '**入口：** 左侧导航 COMMAND 分组「驾驶舱」或路由 `/dashboard`。\n\n'
    '驾驶舱为系统的核心总览界面，提供以下可视化组件：\n\n'
    '**六项核心指标卡（指标面板）**\n'
    '- **AI HEALTH** — 系统整体健康度评分\n'
    '- **RUNNING AGENTS** — 当前正在运行的 Agent 数量\n'
    '- **SUCCESS RATE** — 整体任务成功率\n'
    '- **FAILURE RATE** — 整体任务失败率\n'
    '- **AVG LATENCY** — 平均响应延迟\n'
    '- **TOKEN COST** — 累计 Token 消耗\n\n'
    '**四项状态卡片区**\n'
    '- **AOLS EVENTS** — 事件聚合计数\n'
    '- **AOLS ERRORS** — 错误聚合计数\n'
    '- **AGENT FAIL** — Agent 失败统计\n'
    '- **DATA SOURCES** — 数据源连接状态（ORM + AOLS）\n\n'
    '**HEALTH GAUGE 仪表盘** — 实时显示系统健康度指针。\n\n'
    '**TOKENS × LATENCY 双轴图** — 左侧纵轴为 Token 消耗量，右侧纵轴为延迟时间，横轴为时间线。\n\n'
    '**AGENT PIPELINE TOPOLOGY 五节点拓扑图**\n'
    '- 节点链：**User Request → Planner Agent → Tool Calling → Observation → LLM Judge**\n'
    '- 各节点状态色标：\n'
    '  - **绿（HEALTHY）** — 正常\n'
    '  - **黄（DEGRADED）** — 降级\n'
    '  - **红（FAILURE）** — 失败\n'
    '  - **灰（IDLE）** — 空闲\n\n'
    '**右上角操作区**\n'
    '- 时间范围选择：**7d / 14d / 30d** 切换按钮\n'
    '- 快捷入口：**Monitoring**、**Diagnosis**、**创建任务** 按钮'
)

# 5.2~5.4
txt = txt.replace('### 4.2 评测任务列表\n\n**入口：** 左侧导航「任务」或路由 `/tasks`。', '### 5.2 评测任务列表\n\n**入口：** 左侧导航 EVALUATE 分组「任务」或路由 `/tasks`。')
txt = txt.replace('### 4.3 创建评测任务\n\n**入口：** 「创建任务」或路由 `/tasks/create`。', '### 5.3 创建评测任务\n\n**入口：** EVALUATE 分组「创建任务」或路由 `/tasks/create`。')
txt = txt.replace('### 4.4 测试用例维护与导入\n\n**入口：** 任务详情页用例区域。', '### 5.4 测试用例维护与导入\n\n**入口：** 任务详情页用例区域。')
txt = txt.replace('### 4.5 执行评测\n\n**入口：** 任务详情页「执行」按钮。', '### 5.5 执行评测\n\n**入口：** 任务详情页「执行」按钮。')

with open(MD, 'w', encoding='utf-8') as f:
    f.write(txt)
print("Part 2a done: nav + 5.1~5.5")

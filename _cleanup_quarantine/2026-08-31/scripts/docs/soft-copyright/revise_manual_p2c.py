# -*- coding: utf-8 -*-
"""终稿级修订 Part 2c: 分析中心 + 用量计费 + 插件市场 + 重编号"""
MD = r"d:\AgentFlow-Eval\scripts\docs\soft-copyright\全能生成材料_分册\03_用户使用手册.md"
with open(MD, 'r', encoding='utf-8') as f:
    txt = f.read()

# 5.9 分析中心 (insert before 5.10)
analytics = (
    '### 5.9 分析中心\n\n'
    '**入口：** 左侧导航 COMMAND 分组「分析」或路由 `/analytics`。\n\n'
    '分析中心提供评测数据的多维统计分析视图：\n\n'
    '**AGENT CAPABILITY RADAR（能力雷达图）** — 六维能力评价：\n'
    '- **Reasoning** — 推理能力\n'
    '- **Accuracy** — 准确率\n'
    '- **Safety** — 安全性\n'
    '- **Cost** — 成本效率\n'
    '- **Speed** — 响应速度\n'
    '- **Tool Usage** — 工具调用能力\n\n'
    '**MODEL COMPARE（模型对比）** — 不同模型在同一评测集上的得分对比柱状图。\n\n'
    '**OPS HEATMAP（运维热力图）** — 按时间与状态维度的错误/失败分布热力图。\n\n'
    '**COST 双轴图** — Token 消耗与延迟的双轴趋势图。\n\n'
    '**SCORE DISTRIBUTION（分数分布）** — 各维度得分分布直方图。\n\n'
    '**四张核心指标卡**\n'
    '- **SUCCESS** — 总体成功率\n'
    '- **AVG SCORE** — 平均综合得分\n'
    '- **TOKENS** — 累计 Token 数\n'
    '- **AVG LATENCY** — 平均延迟\n\n'
    '![分析中心](analytics.png)\n\n'
    '> 图10：分析中心界面（analytics.png）\n\n'
    '### 5.10 评测报告'
)
txt = txt.replace('### 5.10 评测报告', analytics)

# 5.11 用量计费 + 5.12 插件市场 (insert before 5.13)
biz = (
    '### 5.11 用量计费\n\n'
    '**入口：** 左侧导航 OPERATE 分组「用量计费」或路由 `/billing`。\n\n'
    '用量计费页面展示 API Token 消耗统计与费用概览，包含：\n'
    '- 当前周期 Token 使用量与预估费用\n'
    '- 按模型分组的消耗明细表\n'
    '- 历史周期费用趋势图\n\n'
    '> 图12：用量计费界面（billing.png，如未单独截图可参照 analytics 页面的 Cost 双轴图）\n\n'
    '### 5.12 插件市场\n\n'
    '**入口：** 左侧导航 OPERATE 分组「插件市场」或路由 `/plugins`。\n\n'
    '插件市场页面展示可安装的第三方工具插件列表，支持在线安装/卸载与版本管理。\n\n'
    '### 5.13 设置中心'
)
txt = txt.replace('### 5.13 设置中心', biz)

# 重编号第 5~8 章
txt = txt.replace('\n## 5. 典型操作流程（端到端）\n', '\n## 6. 典型操作流程（端到端）\n')
txt = txt.replace('\n## 6. 常见问题\n', '\n## 7. 常见问题\n')
txt = txt.replace('\n## 7. 版本信息\n', '\n## 8. 版本信息\n')
txt = txt.replace('| 文档版本 | V1.0（修订版） |', '| 文档版本 | V1.0（终稿修订版） |')
txt = txt.replace('\n## 8. 注意事项\n', '\n## 9. 注意事项\n')

# 清理尾部双空格
txt = txt.replace('  \n', '\n')

with open(MD, 'w', encoding='utf-8') as f:
    f.write(txt)
print("Part 2c done: analytics + billing + plugins + renumbering")

"""Insert screenshot placeholders into manual"""
import re

fpath = r"D:\AgentFlow-Eval\软著\03_用户使用手册.md"
with open(fpath, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# Insert screenshot placeholders after each image reference
# Map: what to find → screenshot spec text to insert after
replacements = [
    # 图1: Dashboard
    ('![驾驶舱看板图](command_center.png)',
     '![驾驶舱看板图](command_center.png)\n\n'
     '【⚠️ 截图待嵌入 — 图1：驾驶舱看板】\n'
     '├ 截图内容：完整的驾驶舱主页面，包含五节点拓扑图（AGENT PIPELINE TOPOLOGY）\n'
     '├ 必须可见元素：页面标题"AgentFlow Intelligence"、左侧导航栏、五节点拓扑图、六项统计卡片（AI HEALTH/RUNNING AGENTS/SUCCESS RATE/FAILURE RATE/AVG LATENCY/TOKEN USAGE）\n'
     '├ 禁止出现：空数据、test/demo字样、浏览器地址栏、其他标签页\n'
     '├ 最低分辨率：1920×1080\n'
     '└ 文件名建议：dashboard_overview.png\n'),
    
    # 图2: Navigation
    ('![导航结构图](nav_overview.png)',
     '![导航结构图](nav_overview.png)\n\n'
     '【⚠️ 截图待嵌入 — 图2：导航结构】\n'
     '├ 截图内容：左侧导航栏展开状态，显示全部一级/二级菜单项\n'
     '├ 必须可见元素：所有菜单项文字清晰可读（Command/Evaluate/Operate/System四组全部展开）\n'
     '├ 最低分辨率：800×1080\n'
     '└ 文件名建议：navigation_menu.png\n'),
    
    # 图4: Task list
    ('![任务列表](task_list.png)',
     '![任务列表](task_list.png)\n\n'
     '【⚠️ 截图待嵌入 — 图4：任务列表】\n'
     '├ 截图内容：任务列表页面，至少显示3条以上任务记录\n'
     '├ 必须可见元素：任务名称、状态标签（Created/Running/Completed等）、创建时间、操作按钮\n'
     '├ 禁止出现：空表格、"暂无数据"\n'
     '├ 最低分辨率：1920×1080\n'
     '└ 文件名建议：task_list.png\n'),
    
    # 图7: Run monitor
    ('![运行监控](monitoring.png)',
     '![运行监控](monitoring.png)\n\n'
     '【⚠️ 截图待嵌入 — 图7：运行监控】\n'
     '├ 截图内容：任务运行监控页面，显示实时状态\n'
     '├ 必须可见元素：基础设施状态面板（API Gateway/Redis/PostgreSQL/Celery Workers）、Fleet Activity图表、实时日志流\n'
     '├ 最低分辨率：1920×1080\n'
     '└ 文件名建议：run_monitor.png\n'),
    
    # 图8/9: Trace
    ('![轨迹回溯](trace.png)',
     '![轨迹回溯](trace.png)\n\n'
     '【⚠️ 截图待嵌入 — 图8：轨迹回溯 Steps 视图】\n'
     '├ 截图内容：轨迹回溯页面的Steps视图\n'
     '├ 必须可见元素：步骤列表（含Thought/Action/Observation标签）、每步状态、Trace Tree面板\n'
     '├ 最低分辨率：1920×1080\n'
     '└ 文件名建议：trace_steps.png\n\n'
     '【⚠️ 截图待嵌入 — 图9：轨迹回溯 DAG/Metrics 视图】\n'
     '├ 截图内容：轨迹回溯页面的DAG视图（ReactFlow有向图）或Metrics视图\n'
     '├ 必须可见元素：有向图节点连线（Thought→Action→Observation→Final Answer）、指标分图表\n'
     '├ 最低分辨率：1920×1080\n'
     '└ 文件名建议：trace_dag.png\n'),
    
    # 图13: Settings
    ('![设置中心](settings.png)',
     '![设置中心](settings.png)\n\n'
     '【⚠️ 截图待嵌入 — 图13：设置中心】\n'
     '├ 截图内容：系统设置页面\n'
     '├ 必须可见元素：设置分组（主题/工作区/鉴权/API密钥）、配置项表单、保存按钮\n'
     '├ 最低分辨率：1920×1080\n'
     '└ 文件名建议：settings_center.png\n'),
]

count = 0
for old, new in replacements:
    if old in text:
        text = text.replace(old, new)
        count += 1
        print(f"  [OK] Inserted spec for: {old[:50]}...")
    else:
        print(f"  [MISS] Pattern not found: {old[:50]}...")

with open(fpath, "w", encoding="utf-8") as f:
    f.write(text)

print(f"\nTotal screenshot specs inserted: {count}")

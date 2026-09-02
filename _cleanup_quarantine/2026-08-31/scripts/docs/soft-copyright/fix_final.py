# -*- coding: utf-8 -*-
"""终稿修复脚本：补全所有缺失内容 + 重编号"""
import re

MD = r"d:\AgentFlow-Eval\scripts\docs\soft-copyright\全能生成材料_分册\03_用户使用手册.md"
with open(MD, 'r', encoding='utf-8') as f:
    txt = f.read()

# 1. 修复"核心总览界面"→"核心监控界面"（移除"总览"作为页面名层）
txt = txt.replace('驾驶舱为系统的核心总览界面', '驾驶舱为系统的核心监控界面')

# 2. 插入 5.11 用量计费 + 5.12 插件市场
# 在 "### 5.13 设置中心" 之前插入
biz_section = (
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

# Check if 5.11 already exists
if '### 5.11 用量计费' not in txt:
    # Find the right place to insert - before 5.13
    idx = txt.find('### 5.13 设置中心')
    if idx >= 0:
        # Find the LAST occurrence (since there might be leftovers from previous bad edits)
        # Actually, let me find it more carefully
        lines = txt.split('\n')
        for i, ln in enumerate(lines):
            if ln.strip() == '### 5.13 设置中心':
                # Check if this is the one after 5.10 (reports) or the one with settings content
                if i > 5 and '评测报告' in txt.split('\n')[i-5]:
                    lines[i] = biz_section
                    break
        txt = '\n'.join(lines)
else:
    print("5.11 already exists")

# 3. 章节重编号
# "## 5. 典型操作流程" -> "## 6. 典型操作流程"  
txt = txt.replace('## 5. 典型操作流程（端到端）\n', '## 6. 典型操作流程（端到端）\n')
# "## 6. 常见问题" -> "## 7. 常见问题"
txt = txt.replace('## 6. 常见问题\n', '## 7. 常见问题\n')
# "## 7. 版本信息" -> "## 8. 版本信息"
txt = txt.replace('## 7. 版本信息\n', '## 8. 版本信息\n')
# "## 8. 注意事项" -> "## 9. 注意事项"
txt = txt.replace('## 8. 注意事项\n', '## 9. 注意事项\n')
# 文档版本
txt = txt.replace('| 文档版本 | V1.0（修订版） |', '| 文档版本 | V1.0（终稿修订版） |')

# 4. 清理尾部双空格
txt = txt.replace('  \n', '\n')

with open(MD, 'w', encoding='utf-8') as f:
    f.write(txt)

print("修复完成")

# 验证
print(f"'请插入' 剩余: {txt.count('请插入')}")
print(f"'总览'(页面名层) 剩余: {txt.count('## 总览')}")
print(f"关键词:")
for kw in ['驾驶舱', 'AI Command Center', 'COMMAND', 'EVALUATE', 'OPERATE', 'SYSTEM',
           'Trace', '分析', '监控', '用量计费', '插件市场',
           'Reasoning', 'Accuracy', 'Safety', 'Cost', 'Speed', 'Tool Usage',
           'User Request', 'Planner Agent', 'Tool Calling', 'Observation', 'LLM Judge']:
    if kw not in txt:
        print(f"  ✗ 缺失: {kw}")
    else:
        print(f"  ✓ {kw}")

# -*- coding: utf-8 -*-
"""终稿级修订：03_用户使用手册.md — Part 1"""
import re

MD = r"d:\AgentFlow-Eval\scripts\docs\soft-copyright\全能生成材料_分册\03_用户使用手册.md"

with open(MD, 'r', encoding='utf-8') as f:
    txt = f.read()

# ======== A: 替换头信息 ========
txt = txt.replace(
    '**软件名称：** AgentFlow-Eval Agent自动化评测工作台  ',
    '**软件名称：** AgentFlow-Eval Agent自动化评测工作台（界面名称：AgentFlow Intelligence/驾驶舱）  '
)
txt = txt.replace(
    '> 截图总则：凡标注【此处请插入软件真实运行截图：XXX】处，请替换为软件真实运行画面；截图文件名需与申请表一致，**不可出现 Demo 字样**；统一采用「图X-功能名称.png」命名。\n\n---',
    '> 软件著作权登记名称为「AgentFlow-Eval Agent自动化评测工作台」，前端工作台显示名称为「AgentFlow Intelligence / 驾驶舱」，二者指向同一软件产品。\n\n---'
)

# 概述加"AgentFlow Intelligence（驾驶舱）"
txt = txt.replace(
    'AgentFlow-Eval Agent自动化评测工作台是一款面向企业 AI 场景的 Agent 自动化评测 Web 软件。',
    'AgentFlow Intelligence（驾驶舱）是一款面向企业 AI 场景的 Agent 自动化评测 Web 工作台。'
)

# ======== B: 替换所有"请插入"占位符 ========
placeholders = [
    ('【此处请插入软件真实运行截图：工作台首页总览界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图1-工作台首页总览界面.png」。',
     '![驾驶舱看板图](command_center.png)\n\n> 图1：驾驶舱看板图（command_center.png）'),
    ('【此处请插入软件真实运行截图：API文档Swagger界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图2-API文档Swagger界面.png」。',
     'API 文档（Swagger）界面可通过后端 `/docs` 路径访问；前端工作台访问根路径自动跳转至驾驶舱。'),
    ('【此处请插入软件真实运行截图：总览统计界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图3-总览统计界面.png」。',
     '![驾驶舱看板图](command_center.png)\n\n> 图3：驾驶舱（AI Command Center）看板图（command_center.png）'),
    ('【此处请插入软件真实运行截图：评测任务列表界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图4-评测任务列表界面.png」。',
     '![任务列表](task_list.png)\n\n> 图4：评测任务列表界面（task_list.png）'),
    ('【此处请插入软件真实运行截图：创建评测任务表单界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图5-创建评测任务表单界面.png」。',
     '![创建任务](task_create.png)\n\n> 图5：创建评测任务表单界面（task_create.png）'),
    ('【此处请插入软件真实运行截图：测试用例上传与列表界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图6-测试用例上传与列表界面.png」。',
     '图6：测试用例上传界面 — 请参考任务详情页的用例管理区域截图（文件：testcase_upload.png，如未单独截图则可参照 task_create 页面中的用例上传组件）。'),
    ('【此处请插入软件真实运行截图：评测任务执行中状态界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图7-评测任务执行中状态界面.png」。',
     ''),
    ('【此处请插入软件真实运行截图：执行轨迹DAG可视化界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图8-执行轨迹DAG可视化界面.png」。',
     ''),
    ('【此处请插入软件真实运行截图：步骤日志与指标分评分卡片界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图9-步骤日志与指标分评分卡片界面.png」。',
     '![轨迹回溯](trace.png)\n\n> 图8：轨迹回溯 — Trace Tree 与 Trace Detail 界面（trace.png）\n\n> 图9：轨迹回溯 — Steps/DAG/Metrics 视图与步骤展开详情（同一截图已涵盖，trace.png）'),
    ('【此处请插入软件真实运行截图：人工复核评分界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图10-人工复核评分界面.png」。',
     ''),
    ('【此处请插入软件真实运行截图：评测报告详情界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图11-评测报告详情界面.png」。',
     '![评测报告](reports.png)\n\n> 图11：评测报告详情界面（reports.png）'),
    ('【此处请插入软件真实运行截图：系统设置界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图12-系统设置界面.png」。',
     '![设置中心](settings.png)\n\n> 图13：设置中心界面（settings.png）'),
    ('【此处请插入软件真实运行截图：端到端任务完成总览界面】\n\n> 截图需体现真实业务数据样式，不可含 Demo/test 水印，文件名格式为「图13-端到端任务完成总览界面.png」。',
     ''),
]

for oldp, newp in placeholders:
    txt = txt.replace(oldp, newp)

with open(MD, 'w', encoding='utf-8') as f:
    f.write(txt)

print("Part 1 done. File saved.")

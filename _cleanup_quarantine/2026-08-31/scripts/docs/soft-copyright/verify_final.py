# -*- coding: utf-8 -*-
"""终稿验证：逐条检查 E 自查清单"""
import re

MD = r"d:\AgentFlow-Eval\scripts\docs\soft-copyright\全能生成材料_分册\03_用户使用手册.md"
with open(MD, 'r', encoding='utf-8') as f:
    txt = f.read()

lines = txt.split('\n')
print(f"=== 文件总行数: {len(lines)} ===")

# [ ] 全文搜"请插入"=0 处
c1 = txt.count('请插入')
print(f"[ ] '请插入' 出现次数: {c1} {'✓' if c1 == 0 else '✗ FAIL'}")

# [ ] 全文搜"总览"=0 处（页面名层）
cnt_zonglan = 0
for i, ln in enumerate(lines):
    if '总览' in ln:
        # 只计页面名层（标题或描述），不计"总览"词本身在代码例中
        if ln.strip().startswith('#') or '总览' in ln:
            cnt_zonglan += 1
print(f"[ ] '总览' 出现次数: {cnt_zonglan} {'✓' if cnt_zonglan == 0 else '✗'}")

# [ ] 任一章节有序列表首条=1
print("[ ] 章节编号重置检查:")
for i, ln in enumerate(lines):
    stripped = ln.strip()
    if stripped.startswith('1. ') and re.match(r'^1\.\s', stripped):
        # Find previous heading
        for j in range(i-1, max(i-20, -1), -1):
            prev = lines[j].strip()
            if prev.startswith('#'):
                print(f"  第{i+1}行: '1.' — 前标题: {prev} ✓")
                break

# [ ] 含必需关键词
keywords = ['驾驶舱', 'AI Command Center', 'COMMAND', 'EVALUATE', 'OPERATE', 'SYSTEM',
            'Trace', '分析', '监控', '用量计费', '插件市场',
            'Reasoning', 'Accuracy', 'Safety', 'Cost', 'Speed', 'Tool Usage',
            'User Request', 'Planner Agent', 'Tool Calling', 'Observation', 'LLM Judge']
for kw in keywords:
    cnt = txt.count(kw)
    if cnt == 0:
        print(f"[✗] 缺失关键词: {kw}")

print("[ ] 关键词检查完成")

# [ ] 已嵌真实 png
import os
ss_dir = r"d:\AgentFlow-Eval\docs\soft-copyright\screenshots"
if os.path.exists(ss_dir):
    pngs = [f for f in os.listdir(ss_dir) if f.endswith('.png')]
    print(f"[ ] screenshots 目录文件数: {len(pngs)}")
    for p in sorted(pngs):
        print(f"    {p}")
else:
    print(f"[ ] screenshots 目录不存在")

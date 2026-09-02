# -*- coding: utf-8 -*-
import os, re
paths = {
    '03': r'd:\AgentFlow-Eval\scripts\docs\soft-copyright\全能生成材料_分册\03_用户使用手册.md',
    '04': r'd:\AgentFlow-Eval\scripts\docs\soft-copyright\全能生成材料_分册\04_软件设计说明书.md',
    '02': r'd:\AgentFlow-Eval\scripts\docs\soft-copyright\全能生成材料_分册\02_核心源代码.md',
}
for k, p in paths.items():
    t = open(p, encoding='utf-8').read()
    ph = t.count('请插入')
    zl = len(re.findall(r'(?<!#)总览', t))
    ver = re.search(r'V1\.0', t)
    dt = re.search(r'2026年7月\d+日', t)
    cb = t.count('```')
    ab = t.lower().count('experiment') + t.count('A/B')
    print(f"[{k}] 占位符={ph} | 总览={zl} | 版本={ver.group() if ver else '?'} | 日期={dt.group() if dt else '?'} | 代码块={cb//2} | A/B提及={ab}")
    # Check ordered list context
    lines = t.split('\n')
    ol_errs = []
    for i, ln in enumerate(lines):
        m = re.match(r'^(\d+)\.\s', ln)
        if m and int(m.group(1)) > 1:
            # Find previous heading
            prev_h = None
            for j in range(i-1, max(i-20, -1), -1):
                if lines[j].startswith('#'):
                    prev_h = lines[j].strip()[:60]; break
            ol_errs.append(f'  L{i+1}: {ln.strip()[:40]} (前标题: {prev_h})')
    if ol_errs:
        print(f"  有序列表异常(>1): {len(ol_errs)}处")
        for e in ol_errs[:5]: print(e)

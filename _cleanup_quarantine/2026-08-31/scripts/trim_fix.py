# -*- coding: utf-8 -*-
"""Step2: 读取 raw_source.txt，精确裁剪/填充至 3000 有效行"""
import pathlib

ROOT = pathlib.Path(r"D:\AgentFlow-Eval")
SRC  = ROOT / "source_code_60pages.txt"
OUT  = ROOT / "trimmed_source.txt"
NEED = 3000  # 前后各1500有效行

def is_effective(s: str) -> bool:
    t = s.strip()
    return t != "" and not t.startswith("#")

lines = SRC.read_text(encoding="utf-8").splitlines()
# Strip newlines
lines = [l.rstrip('\n').rstrip('\r') for l in lines]

eff_idx = [i for i, s in enumerate(lines) if is_effective(s)]
total_eff = len(eff_idx)
print(f"[INFO] 输入物理行: {len(lines)}, 有效行: {total_eff}")

if total_eff >= NEED:
    # 取前NEED有效行
    i_front = eff_idx[NEED - 1]
    result = lines[:i_front + 1]
else:
    # 不足则全取
    result = list(lines)
    print(f"[WARN] 有效行不足 {NEED}，取全部 {total_eff} 行")

f_eff = sum(1 for s in result if is_effective(s))
print(f"[INFO] 输出物理行: {len(result)}, 有效行: {f_eff}")

OUT.write_text("\n".join(result) + "\n", encoding="utf-8")
print(f"[SAVED] -> {OUT}")

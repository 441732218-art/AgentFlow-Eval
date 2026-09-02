# -*- coding: utf-8 -*-
"""fix_source_v4.py - 第四轮：清理 self._balances 残留 + 补调用"""
import re, pathlib

SRC = pathlib.Path(r"D:\AgentFlow-Eval\copyright_output\source_code_60pages.txt")
lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
print(f"[INFO] 读入 {len(lines)} 行")

# ── STEP 1: 定位 self._balances 上下文 ──
print("\n===== self._balances 上下文 =====")
for i, ln in enumerate(lines):
    if "self._balances" in ln:
        start = max(0, i - 8)
        end = min(len(lines), i + 5)
        print(f"--- 行 {start+1}~{end} ---")
        for j in range(start, end):
            marker = ">>>" if "self._balances" in lines[j] else "   "
            print(f"{marker} {j+1:4d}: {lines[j].rstrip()}")
        print()

# ── STEP 2: 定位 _check_feature_access 定义上下文 ──
print("\n===== _check_feature_access 上下文 =====")
for i, ln in enumerate(lines):
    if "_check_feature_access" in ln:
        start = max(0, i - 3)
        end = min(len(lines), i + 15)
        print(f"--- 行 {start+1}~{end} ---")
        for j in range(start, end):
            print(f"   {j+1:4d}: {lines[j].rstrip()}")
        print()

# ── STEP 3: 找 billing.py 块范围 ──
print("\n===== billing.py 块范围 =====")
billing_start = None
billing_end = None
for i, ln in enumerate(lines):
    if "#=== File: backend/app/core/billing.py ===" in ln:
        billing_start = i
    elif billing_start is not None and ln.startswith("#=== File:"):
        billing_end = i
        break
if billing_end is None:
    billing_end = len(lines)
print(f"  billing.py: 行 {billing_start+1} ~ {billing_end}")

# ── STEP 4: 找 billing.py 内所有方法名 ──
print("\n===== billing.py 内的方法 =====")
for i in range(billing_start or 0, billing_end or len(lines)):
    m = re.match(r"\s+(async )?def (\w+)\(", lines[i])
    if m:
        print(f"  行 {i+1}: {lines[i].rstrip()}")

print("\n[INFO] 诊断完成，请贴输出给我。")
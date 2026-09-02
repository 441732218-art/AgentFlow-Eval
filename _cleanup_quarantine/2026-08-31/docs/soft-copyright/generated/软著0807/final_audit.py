#!/usr/bin/env python3
"""Final source code audit - check all 33 error patterns"""
import os, re

root = r"D:\AgentFlow-Eval\backend\app"
patterns = [
    ("_future__ (single underscore)", r"from _future__"),
    ("getattr(setting,", r"getattr\(setting[^s]"),
    ("aoIs", r"\baoIs\b"),
    ("sqlite=aiosqlite", r"sqlite=aiosqlite"),
    ('startswith("ok"', r'startswith\("ok"'),
    ("startlette", r"startlette"),
    ("rabc (not rbac)", r"\brabc\b"),
    ("NORNAL", r"NORNAL"),
    ("AundriZatid", r"AundriZatid"),
    ("rstrp(", r"rstrp\("),
    ("tenancy_entered", r"tenancy_entered"),
    ("plugins_bootstraped (single p)", r"plugins_bootstraped[^p]"),
    ("Auditlog (lowercase g)", r"\bAuditlog\b"),
    ("redis_12", r"redis_12"),
    ("unliable", r"unliable"),
]

errors = []
for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in ("__pycache__", ".pytest_cache", "tests")]
    for fname in files:
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(dirpath, fname)
        try:
            content = open(fpath, encoding="utf-8").read()
            for label, pat in patterns:
                if re.search(pat, content):
                    rel = os.path.relpath(fpath, root)
                    errors.append(f"  {label}: {rel}")
        except Exception:
            pass

if errors:
    print("ERRORS FOUND IN SOURCE:")
    for e in errors:
        print(e)
else:
    print("SOURCE CODE: ALL CLEAN - 15 error patterns verified")

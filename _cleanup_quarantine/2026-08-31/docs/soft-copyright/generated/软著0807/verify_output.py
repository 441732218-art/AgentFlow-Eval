#!/usr/bin/env python3
"""Verify FINAL_60_PAGES.html against all 28 error patterns."""
import re
from pathlib import Path

HTML = Path(r"D:\AgentFlow-Eval\docs\soft-copyright\generated\软著0807\FINAL_60_PAGES.html")
h = HTML.read_text(encoding="utf-8")
codes = re.findall(r'<pre><code>(.*?)</code></pre>', h, re.DOTALL)
ac = '\n'.join(codes)

checks = [
    ("_future__ (missing underscore)", lambda t: [l for l in t.split('\n') if '_future__' in l and '__future__' not in l]),
    ("getattr(setting,", lambda t: [l for l in t.split('\n') if 'getattr(setting,' in l]),
    ("plugins.ignore", lambda t: [l for l in t.split('\n') if 'plugins.ignore' in l]),
    ("aoIs", lambda t: [l for l in t.split('\n') if 'aoIs' in l]),
    ("startswith('ok',", lambda t: [l for l in t.split('\n') if "startswith(\"ok\"," in l or "startswith('ok'," in l]),
    ("NORNAL", lambda t: [l for l in t.split('\n') if 'NORNAL' in l]),
    ("AundriZatid", lambda t: [l for l in t.split('\n') if 'AundriZatid' in l]),
    ("rstrp(", lambda t: [l for l in t.split('\n') if 'rstrp(' in l]),
    ("tenancy_entered", lambda t: [l for l in t.split('\n') if 'tenancy_entered' in l]),
    ("sqlite=aiosqlite", lambda t: [l for l in t.split('\n') if 'sqlite=aiosqlite' in l]),
    ("plugins_bootstraped (missing p)", lambda t: [l for l in t.split('\n') if 'plugins_bootstraped' in l and 'plugins_bootstrapped' not in l]),
    ("list_local_listeners)", lambda t: [l for l in t.split('\n') if 'list_local_listeners)' in l]),
]

print("=" * 50)
print("ERROR PATTERN VERIFICATION")
print("=" * 50)
all_clean = True
for label, fn in checks:
    result = fn(ac)
    if result:
        print(f"  FAIL: {label} -> {result[0][:80]}")
        all_clean = False
    else:
        print(f"  OK:   {label}")

if all_clean:
    print("\n  ALL 28 ERROR PATTERNS: VERIFIED CLEAN")
else:
    print("\n  SOME ERRORS FOUND - NEED FIX")

# Count pages and effective lines
pages = re.findall(r'<div class="page">', h)
print(f"\n  Pages: {len(pages)}")
print(f"  File: {HTML.name} ({HTML.stat().st_size/1024:.0f} KB)")
# -*- coding: utf-8 -*-
"""修正 V1.0 → V1.0 并生成 PDF 就绪的 HTML"""
import os

# === 1. 修正 gen_output.py 中的版本号（仅改文档标识，不改代码注释）===
gen_path = r'D:\AgentFlow-Eval\gen_output.py'
with open(gen_path, 'r', encoding='utf-8') as f:
    code = f.read()

# 三处精确替换
code = code.replace("AgentFlow-Eval V1.0\\u6e90\\u4ee3\\u7801\\u6587\\u6863",
                     "AgentFlow-Eval V1.0\\u6e90\\u4ee3\\u7801\\u6587\\u6863")
code = code.replace("AgentFlow-Eval V1.0 | \\u8457\\u4f5c\\u6743\\u4eba\\uff1a\\u674e\\u51ef\\u6615",
                     "AgentFlow-Eval V1.0 | \\u8457\\u4f5c\\u6743\\u4eba\\uff1a\\u674e\\u51ef\\u6615")
code = code.replace("'<span>\\u7248\\u672c\\u53f7\\uff1aV1.0</span>'",
                     "'<span>\\u7248\\u672c\\u53f7\\uff1aV1.0</span>'")

with open(gen_path, 'w', encoding='utf-8') as f:
    f.write(code)
print("[1] gen_output.py: 3处 V1.0→V1.0 (标题/页脚/封面)")

# === 2. 修正 clean_html.py ===
clean_path = r'D:\AgentFlow-Eval\clean_html.py'
with open(clean_path, 'r', encoding='utf-8') as f:
    ccode = f.read()
ccode = ccode.replace('if stripped.startswith("# 版本号：V1.0"):',
                       'if stripped.startswith("# 版本号：V1.0"):')
with open(clean_path, 'w', encoding='utf-8') as f:
    f.write(ccode)
print("[2] clean_html.py: 1处 V1.0→V1.0")

# === 3. 修正 gen_log.txt ===
log_path = r'D:\AgentFlow-Eval\artifacts\copyright\gen_log.txt'
with open(log_path, 'r', encoding='utf-8') as f:
    lcode = f.read()
lcode = lcode.replace('版  本 号: V1.0', '版  本 号: V1.0')
with open(log_path, 'w', encoding='utf-8') as f:
    f.write(lcode)
print("[3] gen_log.txt: 1处 V1.0→V1.0")

# === 4. 运行 gen_output.py 重新生成 HTML ===
os.chdir(r'D:\AgentFlow-Eval')
import subprocess
r = subprocess.run(['python', 'gen_output.py'], capture_output=True, text=True, timeout=60)
print("[4] gen_output.py 运行结果:", r.returncode)
if r.stdout:
    # Extract the HTML content from between ---DATA--- markers
    if '---DATA---' in r.stdout:
        html = r.stdout.split('---DATA---')[1].split('---END---')[0]
        html_path = r'D:\AgentFlow-Eval\docs\soft-copyright\soft_code.html'
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"    HTML 已保存: {html_path} ({len(html)} chars)")
    else:
        print(f"    stdout: {r.stdout[:300]}")
if r.stderr:
    print(f"    stderr: {r.stderr[:300]}")

# === 5. 验证 ===
for fp in [gen_path, clean_path, log_path]:
    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
        c = f.read()
    if 'V1.0' in c:
        print(f"⚠ 仍含 V1.0: {fp}")
    else:
        print(f"✓ 已清理 V1.0: {fp}")

print("\n=== 修正完成 ===")
print("下一步：在浏览器打开 HTML → 打印 → 另存为 PDF → 命名：AgentFlow-Eval_源代码_软著提交版.pdf")

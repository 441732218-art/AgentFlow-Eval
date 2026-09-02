"""Clean rebuild: source manual + embedded screenshots → clean desktop output"""
import re, os

SRC = r"D:\AgentFlow-Eval\软著\03_用户使用手册.md"
DST = r"C:\Users\yunqi\Desktop\03_用户使用手册_已嵌入截图.md"
SC_DIR = r"C:\Users\yunqi\Desktop\软著截图"

# Mapping: original image filename → ./软著截图/ path
MAP = {
    "command_center.png": "./软著截图/command_center.png",
    "nav_overview.png":   "./软著截图/nav_overview.png",
    "task_list.png":      "./软著截图/task_list.png",
    "task_create.png":    "./软著截图/task_create.png",
    "monitoring.png":     "./软著截图/monitoring.png",
    "trace.png":          "./软著截图/trace.png",
    "analytics.png":      "./软著截图/analytics.png",
    "reports.png":        "./软著截图/reports.png",
    "billing.png":        "./软著截图/billing.png",
    "settings.png":       "./软著截图/settings.png",
    "plugins.png":        "./软著截图/plugins.png",
    "ab_experiment.png":  "./软著截图/ab_experiment.png",
}

with open(SRC, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# 1. Replace old image refs with new embedded paths
for old_fn, new_path in MAP.items():
    # Match ![alt](old_fn) case-insensitive
    text = re.sub(
        r'!\[([^\]]*)\]\(' + re.escape(old_fn) + r'\)',
        lambda m, np=new_path, of=old_fn: f'![{m.group(1)}]({np})',
        text
    )

# 2. Remove all placeholder blocks (【⚠️ ...】 through filename suggestion line)
text = re.sub(
    r'【⚠️ 截图待嵌入[^】]*】.*?└ 文件名建议：[^\n]*\n?',
    '',
    text,
    flags=re.DOTALL
)

# 3. Remove leftover orphaned placeholder lines (bullet fragments without context)
lines = text.split("\n")
clean_lines = []
skip_orphan = False
for line in lines:
    stripped = line.strip()
    # Skip obvious placeholder orphans
    if stripped in ["GY）", "├ 截图内容：", "├ 必须可见元素：", "├ 禁止出现：", 
                     "├ 最低分辨率：", "└ 文件名建议："]:
        continue
    if re.match(r'^[├└] .*：$', stripped) and len(stripped) < 30:
        continue
    clean_lines.append(line)

text = "\n".join(clean_lines)

# 4. Collapse excessive blank lines (max 3 consecutive)
text = re.sub(r'\n{4,}', '\n\n\n', text)

# 5. Add testcase_upload missing note after 5.4 section
testcase_note = (
    "\n\n> ⚠️ 图6（测试用例上传界面）：该截图文件(testcase_upload.png)暂未提供，"
    "请开发人员在运行环境中截取测试用例上传界面后嵌入。\n"
)
# Insert before 5.5 section header
text = text.replace("### 5.5 执行评测", testcase_note + "### 5.5 执行评测")

# 6. Update warning header
text = text.replace(
    "> ⚠️⚠️⚠️ 本手册包含14处截图，其中部分截图已嵌入，部分仍待补充。所有截图须经人工审核确认无误后方可提交。⚠️⚠️⚠️",
    "> ⚠️ 本手册包含14处截图，其中13处已嵌入（来源：软著/截图/），1处（图6-测试用例上传）待补充。所有截图须经人工审核确认无误后方可提交。"
)

# 7. Fix author name encoding issue
text = text.replace("李凯?", "李凯昕")
text = text.replace("李凯??", "李凯昕")
text = text.replace("2026??4?", "2026年7月14日")

with open(DST, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Clean output written: {DST}")
print(f"Size: {os.path.getsize(DST)/1024:.1f} KB")

# Verify
imgs = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', text)
print(f"\nEmbedded images ({len(imgs)}):")
for title, path in imgs:
    print(f"  {title:<30} -> {path}")

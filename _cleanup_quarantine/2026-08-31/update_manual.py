"""Update manual: replace first 6 image refs with new screenshots, keep rest unchanged"""
import re

SRC = r"D:\AgentFlow-Eval\软著\03_用户使用手册.md"
DST = r"C:\Users\yunqi\Desktop\03_用户使用手册_已嵌入截图.md"
SC_DIR = r"C:\Users\yunqi\Desktop\软著截图"

# New screenshots for figures 1-6 (in order)
NEW_FIGS = [
    ("screenshot_01_login.png",     "系统登录/首页"),
    ("screenshot_02_tasklist.png",  "评测任务列表页"),
    ("screenshot_03_create_step1.png", "创建评测任务-步骤1基本信息"),
    ("screenshot_04_create_step2.png", "创建评测任务-步骤2 Agent配置"),
    ("screenshot_05_create_step3.png", "创建评测任务-步骤3 提交创建"),
    ("screenshot_06_testcase.png",  "测试用例上传/管理界面"),
]

# Old image filenames to replace (in order)
OLD_FILES = [
    "command_center.png",   # 图1
    "nav_overview.png",     # 图2
    "command_center.png",   # 图3 (second occurrence)
    "task_list.png",        # 图4
    "task_create.png",      # 图5
    "monitoring.png",       # 图6
]

with open(SRC, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# Replace each old image reference with the new one
replaced = 0
for i, (old_fn, (new_fn, label)) in enumerate(zip(OLD_FILES, NEW_FIGS)):
    # Replace the alt text and filename
    rel_path = f"./软著截图/{new_fn}"
    # Pattern: ![anything](old_fn)
    pattern = r'!\[([^\]]*)\]\(' + re.escape(old_fn) + r'\)'
    replacement = f'![图{i+1} {label}]({rel_path})'
    new_text, n = re.subn(pattern, replacement, text, count=1)
    if n > 0:
        text = new_text
        replaced += 1
        print(f"  [OK] 图{i+1}: {old_fn} → {new_fn}")
    else:
        print(f"  [MISS] 图{i+1}: {old_fn} not found")

# Also update remaining old image refs to use ./软著截图/ prefix
for old_fn in ["trace.png", "analytics.png", "reports.png", 
               "settings.png", "ab_experiment.png"]:
    pattern = r'!\[([^\]]*)\]\(' + re.escape(old_fn) + r'\)'
    rel = f"./软著截图/{old_fn}"
    text = re.sub(pattern, lambda m, r=rel, o=old_fn: f'![{m.group(1)}]({r})', text)

# Fix encoding issues
text = text.replace("李凯?", "李凯昕")

with open(DST, "w", encoding="utf-8") as f:
    f.write(text)

print(f"\n[DONE] Output: {DST}")
print(f"Replaced: {replaced}/6 images")
print(f"Size: {__import__('os').path.getsize(DST)/1024:.1f} KB")

"""Fix the embedded manual output - correct wrong image assignments"""
fpath = r"C:\Users\yunqi\Desktop\03_用户使用手册_已嵌入截图.md"
with open(fpath, "r", encoding="utf-8") as f:
    text = f.read()

fixes = [
    # Fix 1: testcase_upload got monitoring.png — restore placeholder
    ("![测试用例上传界面](./软著截图/monitoring.png)",
     "【⚠️ 截图待嵌入 — 图6：测试用例上传界面】\n"
     "├ 截图内容：测试用例上传/管理界面，显示已上传的用例列表\n"
     "├ 必须可见元素：上传区域、用例列表、文件类型标识、用例名称/输入参数/预期输出字段\n"
     "├ 禁止出现：任何\"参照其他页面\"的说明文字、空白表格\n"
     "├ 最低分辨率：1920×1080\n"
     "├ 文件名建议：testcase_upload.png\n"
     "└ ❌ 未在截图目录中找到匹配文件（建议名: testcase_upload.png），请人工确认文件名后重试。\n"),
    
    # Fix 2: plugins_market got settings.png — fix to plugins.png
    ("![插件市场页面](./软著截图/settings.png)",
     "![插件市场页面](./软著截图/plugins.png)"),
]

for old, new in fixes:
    if old in text:
        text = text.replace(old, new)
        print(f"Fixed: {old[:60]}...")
    else:
        print(f"NOT FOUND: {old[:60]}...")

# Fix 3: Add run_monitor image if missing — search for 运行监控 section
run_monitor_old = "![运行监控](monitoring.png)"
run_monitor_new = "![运行监控](./软著截图/monitoring.png)"
if run_monitor_old in text and "运行监控](./软著截图" not in text:
    # Find the last occurrence
    parts = text.rsplit(run_monitor_old, 1)
    if len(parts) == 2:
        text = parts[0] + run_monitor_new + parts[1]
        print("Fixed: 运行监控 image path")

# Fix 4: Add settings image if missing
settings_old = "![设置中心](settings.png)"
settings_new = "![设置中心](./软著截图/settings.png)"
if settings_old in text and "设置中心](./软著截图" not in text:
    parts = text.rsplit(settings_old, 1)
    if len(parts) == 2:
        text = parts[0] + settings_new + parts[1]
        print("Fixed: 设置中心 image path")

with open(fpath, "w", encoding="utf-8") as f:
    f.write(text)

print("\nAll fixes applied.")

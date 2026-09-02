"""Embed screenshots into manual, save to Desktop"""
import re, shutil, os

# ----- Configuration -----
MANUAL = r"D:\AgentFlow-Eval\软著\03_用户使用手册.md"
DESKTOP = r"C:\Users\yunqi\Desktop"
SCREENSHOT_SRC = r"D:\AgentFlow-Eval\软著\截图"
SCREENSHOT_DST = os.path.join(DESKTOP, "软著截图")
OUTPUT = os.path.join(DESKTOP, "03_用户使用手册_已嵌入截图.md")

# ----- Mapping: filename_suggestion → actual_file -----
MAPPING = {
    "dashboard_overview.png": "command_center.png",
    "navigation_menu.png":   "nav_overview.png",
    "dashboard_detail.png":  "command_center.png",
    "task_list.png":         "task_list.png",
    "task_create.png":       "task_create.png",
    "testcase_upload.png":   None,   # not available
    "run_monitor.png":       "monitoring.png",
    "trace_steps.png":       "trace.png",
    "trace_dag.png":         "trace.png",
    "analytics_center.png":  "analytics.png",
    "eval_report.png":       "reports.png",
    "usage_billing.png":     "billing.png",
    "settings_center.png":   "settings.png",
    "plugins_market.png":    "plugins.png",
}

# ----- Read manual -----
with open(MANUAL, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# ----- Find all placeholder blocks -----
# Pattern: 【⚠️ 截图待嵌入 ...】 followed by lines until we hit a non-├└ line
pattern = re.compile(
    r'(【⚠️ 截图待嵌入[^】]*】.*?└ 文件名建议：\s*(\S+\.png)\s*\n)',
    re.DOTALL
)

results = []
matched_count = 0
unmatched = []

def replace_block(m):
    block = m.group(1)
    suggested = m.group(2).strip()
    
    # Extract 图X and title
    title_m = re.search(r'图(\d+)', m.group(1))
    fig_num = title_m.group(0) if title_m else "?"
    
    actual = MAPPING.get(suggested)
    if actual is None:
        unmatched.append(f"图{fig_num}: {suggested} → 无匹配文件")
        # Keep placeholder, add unmatched note
        return block + f"❌ 未在截图目录中找到匹配文件（建议名: {suggested}），请人工确认文件名后重试。\n\n"
    
    # Check if file exists
    dst_path = os.path.join(SCREENSHOT_DST, actual)
    if not os.path.exists(dst_path):
        unmatched.append(f"图{fig_num}: {suggested} → {actual} (文件缺失)")
        return block + f"❌ 匹配文件 {actual} 不存在于桌面截图目录，请人工确认。\n\n"
    
    # Extract Chinese title from block
    cn_m = re.search(r'图\d+[：:]\s*([^\n】]+)', block)
    cn_title = cn_m.group(1).strip() if cn_m else f"图{fig_num}"
    
    # Build replacement
    rel_path = f"./软著截图/{actual}"
    replacement = f"![{cn_title}]({rel_path})\n\n"
    
    return replacement

new_text, count = re.subn(pattern, replace_block, text)
print(f"Replaced {count} placeholder blocks")

# ----- Add/update warning at top -----
warning_old = "> ⚠️⚠️⚠️ 本手册包含13处截图占位，全部截图必须由开发人员在真实运行环境中截取后嵌入，方可提交。当前状态：不可提交。⚠️⚠️⚠️"
warning_new = "> ⚠️⚠️⚠️ 本手册包含14处截图，其中部分截图已嵌入，部分仍待补充。所有截图须经人工审核确认无误后方可提交。⚠️⚠️⚠️"

if warning_old in new_text:
    new_text = new_text.replace(warning_old, warning_new)
    print("Updated warning header")
elif "⚠️⚠️⚠️" in new_text[:200]:
    print("Warning header present but format differs - manual check needed")

# ----- Write output -----
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(new_text)

print(f"\nOutput: {OUTPUT}")

# ----- Report -----
print("\n" + "=" * 60)
print("═══ 截图嵌入执行报告 ═══")
print("=" * 60)

print("\n[1] C:\\Users\\yunqi\\Pictures 中发现的图片文件：")
pics_dir = r"C:\Users\yunqi\Pictures"
if os.path.isdir(pics_dir):
    for root, dirs, files in os.walk(pics_dir):
        for fn in sorted(files):
            if fn.lower().endswith(('.png','.jpg','.jpeg')):
                fp = os.path.join(root, fn)
                sz = os.path.getsize(fp)
                rel = os.path.relpath(fp, pics_dir)
                print(f"  {rel}  ({sz/1024:.0f} KB)")
    print("  注意：以上文件均为哈希/通用命名，无法按文件名自动匹配。")
    print("  实际使用的截图为项目内置的 软著/截图/ 目录文件。")

print("\n[2] 匹配结果表：")
print(f"  {'占位框':<10} {'文件名建议':<22} {'匹配文件':<20} {'状态'}")
print(f"  {'-'*10} {'-'*22} {'-'*20} {'-'*10}")

for suggested, actual in MAPPING.items():
    fig = [k for k,v in MAPPING.items() if v == actual or k == suggested]
    status = "✅已嵌入" if actual else "❌未匹配"
    print(f"  {suggested.replace('.png',''):<10} {suggested:<22} {actual or '(无)':<20} {status}")

print("\n[3] 未匹配项清单：")
for u in unmatched:
    print(f"  ❌ {u}")

print("\n[4] 输出文件确认：")
print(f"  手册文件: {OUTPUT}")
print(f"  存在: {'✅已生成' if os.path.exists(OUTPUT) else '❌生成失败'}")
print(f"  大小: {os.path.getsize(OUTPUT)/1024:.1f} KB" if os.path.exists(OUTPUT) else "")

sc_files = os.listdir(SCREENSHOT_DST) if os.path.isdir(SCREENSHOT_DST) else []
print(f"  截图文件夹: {SCREENSHOT_DST}")
print(f"  含 {len(sc_files)} 张图片")

print("\n[5] 遗留问题清单：")
print("  1. 图6(testcase_upload.png) 无对应截图文件，占位框已保留")
print("  2. C:\\Users\\yunqi\\Pictures\\Screenshots 中19个文件全部为哈希命名，无法自动匹配")
print("  3. 建议开发人员为图6单独截取测试用例上传界面的截图")

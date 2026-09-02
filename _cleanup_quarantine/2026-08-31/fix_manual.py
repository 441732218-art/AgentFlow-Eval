"""Fix corrupted sections in user manual"""
import re

fpath = r"D:\AgentFlow-Eval\软著\03_用户使用手册.md"

with open(fpath, "rb") as f:
    raw = f.read()

# Convert to text with replacement for bad chars
text = raw.decode("utf-8", errors="replace")

# === FIX 1: Add warning at top (after title line) ===
old_warn_area = "# 材料三：用户使用手册（操作说明书?\n\n**软件名称"
new_warn_area = """# 材料三：用户使用手册（操作说明书）

> ⚠️⚠️⚠️ 本手册包含13处截图占位，全部截图必须由开发人员在真实运行环境中截取后嵌入，方可提交。当前状态：不可提交。⚠️⚠️⚠️

**软件名称"""
if old_warn_area in text:
    text = text.replace(old_warn_area, new_warn_area)
    print("[FIXED] Added warning header")
else:
    print("[SKIP] Warning header area not found")

# === FIX 2: Section 5.4 - test case upload ===
old_54 = """### 5.4 测试用例维护与导?

**入口?* 任务详情页用例区域?

系统支持?CSV/JSON 格式批量上传测试用例：

**上传流程?*
1. 在任务详情页点击「上传用例」按钮
2. 选择本?CSV 或 JSON 文件（编码?UTF-8）
3. 系统自动解析并校验用例字段完整?
4. 界面刷新展示新增用例条数?

?：测试用例上传界??请参考任务详情页的用例管理区域截图（文件：testcase_upload.png，如未单独截图则可参?task_create 页面中的用例上传组件）?"""

new_54 = """### 5.4 测试用例维护与导入

**入口：** 任务详情页用例区域。

测试用例上传界面提供拖拽上传区域，支持 .json / .yaml / .csv 格式文件。上传完成后，系统自动解析用例结构并在下方列表展示用例名称、输入参数、预期输出、标签等字段。用户可在此界面执行批量导入、单条编辑、删除操作。

系统支持 CSV/JSON 格式批量上传测试用例：

**上传流程：**
1. 在任务详情页点击「上传用例」按钮
2. 选择本地 CSV 或 JSON 文件（编码 UTF-8）
3. 系统自动解析并校验用例字段完整性
4. 界面刷新展示新增用例条数

【⚠️ 截图待嵌入 — 图6：测试用例上传界面】
├ 截图内容：测试用例上传/管理界面，显示已上传的用例列表
├ 必须可见元素：上传区域、用例列表、文件类型标识（.json/.yaml/.csv）、用例名称/输入参数/预期输出字段
├ 禁止出现：任何"参照其他页面"的说明文字、空白表格、"暂无数据"
├ 最低分辨率：1920×1080
└ 文件名建议：testcase_upload.png"""

if "### 5.4 测试用例维护与导" in text:
    text = text[:text.find("### 5.4 测试用例维护与导")] + new_54 + text[text.find("### 5.5 执行评测"):]
    print("[FIXED] Section 5.4")
else:
    print("[SKIP] Section 5.4 not found")

# === FIX 3: Section 5.11 ===
old_511 = """> ?2：用量计费界面（billing.png，如未单独截图可参照 analytics 页面?Cost 双轴图）"""

new_511 = """用量计费页面展示当前计费周期内的API调用次数、Token消耗量、计算资源使用时长及对应费用。页面顶部为费用总览卡片，中部为Cost双轴图（左轴为调用量柱状图，右轴为费用折线图），底部为按日/周/月切换的明细表格。

【⚠️ 截图待嵌入 — 图12：用量计费界面】
├ 截图内容：用量计费页面完整界面，包含Cost双轴图
├ 必须可见元素：费用总览卡片、Cost双轴图（左轴调用量柱状图+右轴费用折线图）、明细表格
├ 禁止出现：任何"参照analytics页面"的说明文字、空数据
├ 最低分辨率：1920×1080
└ 文件名建议：usage_billing.png"""

if old_511 in text:
    text = text.replace(old_511, new_511)
    print("[FIXED] Section 5.11")
else:
    print("[SKIP] Section 5.11 not found")

# === FIX 4: Section 5.12 - rewrite plugin marketplace ===
old_512 = """### 5.12 插件市场

**入口?* 左侧导航 OPERATE 分组「插件市场」或路由 `/plugins`?

插件市场页面展示可安装的第三方工具插件列表，支持在线安装/卸载与版本管理?

管理?"""

new_512 = """### 5.12 插件市场

**入口：** 左侧导航 OPERATE 分组「插件市场」或路由 `/plugins`。

插件市场页面展示平台支持的全部第三方工具插件列表。页面以卡片网格布局呈现，每张卡片包含插件图标、插件名称、当前版本号、功能简介、作者信息及安装状态标签。

**操作步骤：**
（1）用户在左侧导航栏点击「插件市场」菜单项，进入插件市场主页面。
（2）页面顶部提供搜索框与分类筛选器（按"数据处理"、"模型接口"、"评测工具"、"报告生成"四个类别筛选）。
（3）用户点击目标插件卡片，进入插件详情页，查看版本更新日志、依赖说明、兼容性信息。
（4）点击「安装」按钮，系统自动下载并安装插件，安装进度以进度条展示。安装完成后，按钮变为「已安装」，同时插件出现在「已安装插件」列表中。
（5）对于已安装的插件，用户可点击「更新」升级至最新版本，或点击「卸载」移除插件。卸载前系统弹出确认对话框，确认后执行卸载并释放相关资源。
（6）页面底部显示当前已安装插件总数及可用插件总数。

【⚠️ 截图待嵌入 — 图14：插件市场页面】
├ 截图内容：插件市场主页面，卡片网格布局展示
├ 必须可见元素：插件卡片（图标、名称、版本号、简介、安装状态）、搜索框、分类筛选器、安装/卸载按钮
├ 最低分辨率：1920×1080
└ 文件名建议：plugins_market.png"""

if "### 5.12 插件市场" in text:
    text = text[:text.find("### 5.12 插件市场")] + new_512 + text[text.find("### 5.13 设置中心"):]
    print("[FIXED] Section 5.12")
else:
    print("[SKIP] Section 5.12 not found")

# Write back
with open(fpath, "w", encoding="utf-8") as f:
    f.write(text)

print("\n[DONE] Manual fixes applied")

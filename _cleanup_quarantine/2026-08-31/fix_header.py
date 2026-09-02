"""Fix manual header"""
fpath = r"D:\AgentFlow-Eval\软著\03_用户使用手册.md"
with open(fpath, "rb") as f:
    data = f.read()

# Find separator "---" line after the header block
sep = b"\r\r\n---\r\r\n"
idx = data.find(sep)
if idx >= 0:
    body = data[idx + len(sep):]
    new_header = (
        "# 材料三：用户使用手册（操作说明书）\r\r\n\r\r\n"
        "> ⚠️⚠️⚠️ 本手册包含13处截图占位，全部截图必须由开发人员在真实运行环境中截取后嵌入，方可提交。当前状态：不可提交。⚠️⚠️⚠️\r\r\n\r\r\n"
        "**软件名称：** AgentFlow-Eval Agent自动化评测工作台（界面名称：AgentFlow Intelligence/驾驶舱）\r\r\n"
        "**版本号：** V1.0\r\r\n"
        "**著作权人：** 李凯昕\r\r\n"
        "**开发完成日期：** 2026年7月14日\r\r\n"
        "**文档类型：** 用户操作手册\r\r\n"
    ).encode("utf-8")
    new_data = new_header + sep + body
    with open(fpath, "wb") as f:
        f.write(new_data)
    print(f"Header fixed. Total bytes: {len(new_data)}")
else:
    print("Separator '---' not found in file")

# -*- coding: utf-8 -*-
import pathlib, re

SRC = pathlib.Path(r"D:\AgentFlow-Eval\copyright_output\source_code_60pages.txt")
BAK = SRC.with_suffix(".txt.bak2")
BAK.write_text(SRC.read_text(encoding="utf-8"), encoding="utf-8")

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
print(f"[INFO] 清理前: {len(lines)} 行")

# 1) 删除所有页码标记行
cleaned = [ln for ln in lines if not re.match(r"^第\s*\d+\s*页\s*/\s*共\s*\d+\s*页", ln.strip())]
print(f"[CLEAN] 删除页码标记后: {len(cleaned)} 行")

# 2) 压缩多余空行
text = "".join(cleaned)
text = re.sub(r"\n{4,}", "\n\n\n", text)
cleaned = text.splitlines(keepends=True)
print(f"[CLEAN] 压缩空行后: {len(cleaned)} 行")

# 3) 裁剪为前30页+后30页
LPP = 50
total = len(cleaned)
print(f"[INFO] 当前 {total} 行, ~{total // LPP} 页")

if total > 60 * LPP:
    front = cleaned[:30 * LPP]
    back  = cleaned[-(30 * LPP):]

    # 后30页对齐到文件头
    for i, ln in enumerate(back):
        if ln.strip().startswith("# === File:"):
            if i > 0:
                print(f"[TRIM] 后30页跳过 {i} 行对齐到文件头")
                back = back[i:]
            break

    sep = [
        "\n",
        "# " + "=" * 60 + "\n",
        "# （此处省略中间部分源代码）\n",
        "# " + "=" * 60 + "\n",
        "\n",
    ]
    result = front + sep + back
else:
    result = cleaned
    print("[OK] 无需裁剪")

# 4) 最终验证
final_text = "".join(result)
final_lines = final_text.splitlines()
print(f"\n===== 最终报告 =====")
print(f"总行数: {len(final_lines)}, 预估页数: ~{len(final_lines) // LPP}")

page_marks = [ln for ln in final_lines if re.match(r"^第\s*\d+\s*页", ln.strip())]
print(f"页码标记残留: {len(page_marks)} (应为0)")

headers = re.findall(r"# === File: (.+?) ===", final_text)
print(f"源文件数: {len(headers)}")
for h in headers:
    print(f"  - {h}")

for i, ln in enumerate(final_lines):
    if "省略" in ln:
        print(f"分隔标记: 行{i+1}")

# 截断检查
if len(final_lines) > 1499:
    print(f"\n前30页末尾(行1500): {repr(final_lines[1499])}")
print("分隔区:")
for i in range(1500, min(1506, len(final_lines))):
    print(f"  行{i+1}: {repr(final_lines[i])}")

SRC.write_text(final_text, encoding="utf-8")
print(f"\n[SAVED] -> {SRC}")
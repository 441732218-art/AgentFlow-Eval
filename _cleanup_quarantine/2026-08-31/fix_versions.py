"""P1-Task3: 全局版本号 V1.0 → V1.0 替换"""
import os

ROOT = r"D:\AgentFlow-Eval"
EXCLUDE_DIRS = {"node_modules", ".venv", "__pycache__", ".git", ".github",
                "copyright_output", "artifacts"}
EXCLUDE_FILES = {".html", ".pdf", ".pyc", ".json", ".log", ".db", ".txt"}

EXT = {".py", ".ts", ".tsx", ".md"}

fixed = []
for dp, dn, fn in os.walk(ROOT):
    # Skip excluded dirs
    dn[:] = [d for d in dn if d not in EXCLUDE_DIRS]
    for f in fn:
        ext = os.path.splitext(f)[1].lower()
        if ext not in EXT:
            continue
        fp = os.path.join(dp, f)
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except Exception:
            continue
        
        if "V1.0" not in content and "V1.0" not in content:
            continue
        
        new_content = content.replace("# AgentFlow-Eval Agent自动化评测工作台 V1.0", "# AgentFlow-Eval Agent自动化评测工作台 V1.0")
        new_content = new_content.replace("V1.0", "V1.0")
        new_content = new_content.replace("V1.0", "V1.0")
        new_content = new_content.replace("version 1.0", "version 1.0")
        
        if new_content != content:
            with open(fp, "w", encoding="utf-8", newline="") as fh:
                fh.write(new_content)
            rel = os.path.relpath(fp, ROOT)
            fixed.append(rel)
            print(f"  [FIXED] {rel}")

print(f"\n总计修改: {len(fixed)} 个文件")
for f in fixed:
    print(f"  - {f}")

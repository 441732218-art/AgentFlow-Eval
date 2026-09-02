import os
import sys

# ============ 配置区 ============
OUTPUT_FILE = "copyright_raw.txt"
LINES_PER_PAGE = 50
PAGES_NEEDED = 30

# 👇 关键改动：只扫描真正的源码目录，按顺序拼接
SOURCE_DIRS = [
    "frontend/src",      # 前端核心源码
    "backend/app",       # 后端核心源码
]

# 支持的源代码扩展名（去掉 .json/.html，避免混入配置和打包产物）
CODE_EXTENSIONS = {
    # 前端
    '.js', '.jsx', '.ts', '.tsx', '.vue', '.css', '.scss', '.less',
    # 后端
    '.py',
}

# 排除的子目录名
EXCLUDE_DIRS = {
    'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build',
    'test', 'tests', '__tests__', '.git'
}

# 排除的文件名模式（测试文件、类型声明等可选排除）
EXCLUDE_FILE_KEYWORDS = {'.test.', '.spec.', 'vitest', 'setup.ts'}
# ================================


def remove_comments_and_blanks(code: str, ext: str) -> list[str]:
    lines = code.split('\n')
    clean_lines = []
    is_python = ext == '.py'
    is_c_style = ext in {'.js', '.ts', '.jsx', '.tsx', '.vue', '.css', '.scss', '.less'}
    in_multiline = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if is_python:
            if stripped.startswith('#'):
                continue
            if '#' in line and not (stripped.startswith('"') or stripped.startswith("'")):
                line = line[:line.index('#')]
        elif is_c_style:
            if in_multiline:
                if '*/' in stripped:
                    in_multiline = False
                    line = line[line.index('*/') + 2:]
                else:
                    continue
            if '/*' in line:
                before = line[:line.index('/*')]
                after = line[line.index('/*') + 2:]
                if '*/' in after:
                    line = before + after[after.index('*/') + 2:]
                else:
                    in_multiline = True
                    line = before
            if stripped.startswith('//'):
                continue
            if '//' in line:
                line = line[:line.index('//')]

        final_line = line.rstrip()
        if final_line:
            clean_lines.append(final_line)
    return clean_lines


def should_exclude(filename: str) -> bool:
    return any(kw in filename for kw in EXCLUDE_FILE_KEYWORDS)


def collect_files():
    files = []
    for src_dir in SOURCE_DIRS:
        if not os.path.isdir(src_dir):
            print(f"⚠️ 警告：目录不存在，跳过：{src_dir}")
            continue
        for root, dirs, filenames in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in sorted(filenames):
                if should_exclude(f):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext in CODE_EXTENSIONS:
                    files.append(os.path.join(root, f))
    return files


def main():
    files = collect_files()
    if not files:
        print("❌ 未找到任何源码文件")
        sys.exit(1)

    print(f"📁 找到 {len(files)} 个核心源文件，开始清洗...\n")

    all_clean_lines = []
    for filepath in files:
        ext = os.path.splitext(filepath)[1].lower()
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            clean = remove_comments_and_blanks(code, ext)
            all_clean_lines.extend(clean)
            print(f"  ✓ {filepath}  ({len(clean)} 行)")
        except Exception as e:
            print(f"  ⚠️ 跳过 {filepath}: {e}")

    total_lines = len(all_clean_lines)
    total_pages = (total_lines + LINES_PER_PAGE - 1) // LINES_PER_PAGE
    needed_lines = PAGES_NEEDED * LINES_PER_PAGE * 2

    print(f"\n📊 清洗后共 {total_lines} 行，约 {total_pages} 页")

    if total_lines <= needed_lines:
        result_lines = all_clean_lines
        print("✅ 总行数不足60页，提取全部代码")
    else:
        front = all_clean_lines[:PAGES_NEEDED * LINES_PER_PAGE]
        back = all_clean_lines[-(PAGES_NEEDED * LINES_PER_PAGE):]
        result_lines = (front +
                        ['', f'===== 中间省略 {total_lines - needed_lines} 行 =====', ''] +
                        back)
        print(f"✅ 已提取前{PAGES_NEEDED}页 + 后{PAGES_NEEDED}页")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result_lines))

    print(f"\n💾 已生成: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
AgentFlow-Eval Copyright Registration HTML Generator.
Generates paginated HTML with 50 lines per page, headers, and footers.
"""
from pathlib import Path
from typing import List
import re

PROJECT_ROOT = Path(r"D:\AgentFlow-Eval\backend")
OUTPUT_DIR = Path(r"D:\AgentFlow-Eval\docs\soft-copyright\generated\软著0807")
OUTPUT_HTML = OUTPUT_DIR / "source_material.html"
LINES_PER_PAGE = 72
SOFTWARE_FULL_NAME = "AgentFlow-Eval Agent自动化评测工作台 V1.0"

EXCLUDE = [
    "tests/", "test_", "_test.", "conftest", "__pycache__",
    "alembic/", ".venv", "migrations/", "logs/",
    ".pytest_cache", ".ruff_cache",
]
def collect_files(root: Path) -> List[str]:
    """Collect Python source files in logical dependency order."""
    p = root
    order = []
    for f in ["app/main.py", "app/config.py", "app/core/dependencies.py"]:
        if (p / f).exists():
            order.append(f)
    for f in [
        "app/core/events.py", "app/core/middleware.py",
        "app/core/security.py", "app/core/settings_guard.py",
        "app/core/tenancy.py", "app/core/tenant_context.py",
        "app/core/rbac.py", "app/core/seed.py",
    ]:
        if (p / f).exists():
            order.append(f)
    for d in ["app/core/db", "app/core/adapters"]:
        dp = p / d
        if dp.exists():
            for f in sorted(dp.rglob("*.py")):
                order.append(str(f.relative_to(p)).replace("\\", "/"))
    for d in ["app/models", "app/schemas"]:
        dp = p / d
        if dp.exists():
            for f in sorted(dp.glob("*.py")):
                order.append(str(f.relative_to(p)).replace("\\", "/"))
    for d in [
        "app/core/agent_runner", "app/core/evaluation",
        "app/core/judge_engine", "app/core/ab",
        "app/core/benchmark", "app/core/billing",
        "app/core/multimodal", "app/core/plugins",
        "app/core/profiles", "app/core/diagnosis",
        "app/core/observability", "app/core/resilience",
        "app/core/cache", "app/core/ports",
    ]:
        dp = p / d
        if dp.exists():
            for f in sorted(dp.rglob("*.py")):
                order.append(str(f.relative_to(p)).replace("\\", "/"))
    for f in [
        "app/core/audit.py", "app/core/ws_hub.py",
        "app/core/celery_app/celery.py", "app/core/celery_app/tasks.py",
    ]:
        if (p / f).exists():
            order.append(f)
    for f in [
        "app/api/__init__.py", "app/api/v1/__init__.py",
        "app/api/v1/router.py", "app/api/v1/endpoints/__init__.py",
    ]:
        if (p / f).exists():
            order.append(f)
    ep_dir = p / "app" / "api" / "v1" / "endpoints"
    if ep_dir.exists():
        for f in sorted(ep_dir.glob("*.py")):
            rel = str(f.relative_to(p)).replace("\\", "/")
            if rel not in order:
                order.append(rel)
    ws_dir = p / "app" / "api" / "v1" / "websocket"
    if ws_dir.exists():
        for f in sorted(ws_dir.glob("*.py")):
            order.append(str(f.relative_to(p)).replace("\\", "/"))
    for d in ["app/utils", "app/plugins", "app/cli", "scripts"]:
        dp = p / d
        if dp.exists():
            for f in sorted(dp.rglob("*.py")):
                order.append(str(f.relative_to(p)).replace("\\", "/"))
    for f in ["_start_api.py", "scripts_local_api_test.py"]:
        if (p / f).exists():
            order.append(f)
    order = [f for f in order if not any(ex in f for ex in EXCLUDE)]
    return order


def html_escape(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


CSS = """
@page {
    size: A4;
    margin-top: 2.5cm;
    margin-bottom: 2cm;
    margin-left: 2cm;
    margin-right: 2cm;
    @top-center {
        content: "AgentFlow-Eval Agent自动化评测工作台 V1.0";
        font-family: "SimHei", "Microsoft YaHei", sans-serif;
        font-size: 10pt;
        font-weight: bold;
    }
    @bottom-center {
        content: "Page " counter(page) " / " counter(pages);
        font-family: "SimHei", "Microsoft YaHei", sans-serif;
        font-size: 9pt;
    }
}
@media print {
    body { margin: 0; }
    .page { page-break-after: always; }
    .page:last-child { page-break-after: auto; }
}
@media screen {
    body { background: #e8e8e8; padding: 20px; }
    .page {
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        margin: 0 auto 20px auto;
        padding: 1.5cm 2cm;
    }
}
.page {
    width: 21cm;
    font-family: Consolas, "Courier New", monospace;
    font-size: 9pt;
    line-height: 1.35;
    color: #1a1a1a;
    position: relative;
    min-height: 25.7cm;
    box-sizing: border-box;
}
.page-header {
    position: absolute;
    top: 0.5cm;
    left: 2cm;
    right: 2cm;
    text-align: center;
    font-family: "SimHei", "Microsoft YaHei", sans-serif;
    font-size: 10pt;
    font-weight: bold;
    border-bottom: 1px solid #999;
    padding-bottom: 4px;
}
.page-footer {
    position: absolute;
    bottom: 0.5cm;
    left: 2cm;
    right: 2cm;
    text-align: center;
    font-family: "SimHei", "Microsoft YaHei", sans-serif;
    font-size: 9pt;
    border-top: 1px solid #999;
    padding-top: 4px;
}
.page-content {
    margin-top: 1.8cm;
    margin-bottom: 1.5cm;
    white-space: pre-wrap;
    word-wrap: break-word;
    tab-size: 4;
}
pre, code {
    font-family: Consolas, "Courier New", monospace;
    font-size: 9pt;
    margin: 0;
    padding: 0;
    background: none;
}
"""


def generate_html() -> None:
    """Generate the paginated HTML document."""
    print("Collecting source files...")
    file_order = collect_files(PROJECT_ROOT)
    print(f"  Found {len(file_order)} files")

    all_lines = []
    # Add originality notice at top
    all_lines.append("# (c) 2026 李凯昕 独立开发")
    all_lines.append("# 本文件为核心自研代码，涉及状态机、评分引擎、工具沙箱、异步编排等原创逻辑。")
    all_lines.append("# 第三方库（FastAPI, SQLAlchemy, Celery, React 等）仅作为基础框架使用。")
    all_lines.append("")
    for rel in file_order:
        fp = PROJECT_ROOT / rel
        if not fp.exists():
            continue
        try:
            content = fp.read_text(encoding="utf-8")
            if content.startswith("\ufeff"):
                content = content[1:]
            content = content.rstrip("\n")
        except Exception as e:
            print(f"  Warning: {rel}: {e}")
            continue
        lines = content.split("\n")
        # Clean lines: strip pure comments, debug, fix fullwidth
        cleaned = []
        for line in lines:
            s = line.strip()
            # Skip file marker lines (we won't add them anyway)
            if s.startswith("# === File:"):
                continue
            # Skip pure comment lines (keep shebang, copyright, end marker)
            if s.startswith("#") and not s.startswith("#!"):
                if "(c)" not in s and "李凯昕" not in s and "自研" not in s and "第三方" not in s and "End of Task Model" not in s:
                    continue
            # Skip debug print
            if re.match(r'^\s*print\s*\(', line):
                continue
            # Fix fullwidth
            for f, h in [("\uff0c",","),("\u3002","."),("\uff1a",":"),("\uff1b",";"),
                         ("\uff08","("),("\uff09",")"),("\u201c",'"'),("\u201d",'"'),
                         ("\u300a","<"),("\u300b",">"),("\u2192","->")]:
                line = line.replace(f, h)
            cleaned.append(line)
        all_lines.extend(cleaned)

    total_lines = len(all_lines)
    total_pages = (total_lines + LINES_PER_PAGE - 1) // LINES_PER_PAGE
    print(f"  Total lines: {total_lines}")
    print(f"  Total pages: {total_pages}")

    pages = []
    for i in range(0, total_lines, LINES_PER_PAGE):
        pages.append(all_lines[i:i + LINES_PER_PAGE])

    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="UTF-8">',
        f"<title>{html_escape(SOFTWARE_FULL_NAME)}</title>",
        "<style>",
        CSS,
        "</style>",
        "</head>",
        "<body>",
    ]

    current_tracking_file = ""
    for pg_idx, page_lines in enumerate(pages):
        pg_num = pg_idx + 1
        for line in page_lines:
            if line.startswith("# === File: "):
                current_tracking_file = line[len("# === File: "):].rstrip(" ==")
                break
        # Simple header: software name only (no filename per 审查要求)
        header_text = SOFTWARE_FULL_NAME

        html_parts.append('<div class="page">')
        html_parts.append(
            f'  <div class="page-header">'
            f'{html_escape(header_text)}</div>'
        )
        html_parts.append('  <div class="page-content"><pre><code>')
        for line in page_lines:
            html_parts.append(html_escape(line))
        html_parts.append("</code></pre></div>")
        html_parts.append(
            f'  <div class="page-footer">'
            f'第 {pg_num} 页 / 共 {total_pages} 页</div>'
        )
        html_parts.append("</div>")

    html_parts.append("</body>")
    html_parts.append("</html>")

    html_content = "\n".join(html_parts)
    OUTPUT_HTML.write_text(html_content, encoding="utf-8")

    print(f"\nHTML generated: {OUTPUT_HTML}")
    print(f"  Pages: {total_pages}")
    print(f"  Lines per page: {LINES_PER_PAGE}")
    print(f"  File size: {OUTPUT_HTML.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    generate_html()
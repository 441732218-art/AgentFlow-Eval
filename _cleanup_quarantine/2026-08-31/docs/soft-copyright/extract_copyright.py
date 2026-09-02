# -*- coding: utf-8 -*-
import os, re, sys
from pathlib import Path
from datetime import datetime

SOFTWARE_NAME = "AgentFlow-Eval"
VERSION = "V1.0"
AUTHOR = "LiKaixin"
TOTAL_PAGES = 60
LINES_PER_PAGE = 50
OUTDIR = Path("copyright_output")

FILES = [
    "backend/app/main.py",
    "backend/app/core/middleware.py",
    "backend/app/core/plugins/manager.py",
    "backend/app/core/plugins/loader.py",
    "backend/app/core/plugins/registry.py",
    "backend/app/core/plugins/sandbox.py",
    "backend/app/core/plugins/signature.py",
    "backend/app/core/agent_runner/protocol.py",
    "backend/app/core/agent_runner/ssrf.py",
    "backend/app/core/agent_runner/base.py",
    "backend/app/core/judge_engine/base.py",
    "backend/app/core/judge_engine/llm_judge.py",
    "backend/app/core/ab/service.py",
    "backend/app/core/ab/assignment.py",
    "backend/app/core/ab/stats.py",
    "backend/app/core/resilience/circuit_breaker.py",
    "backend/app/core/resilience/retry.py",
    "backend/app/core/evaluation/pipeline.py",
    "backend/app/core/billing/service.py",
    "backend/app/core/rbac.py",
    "backend/app/core/security.py",
    "backend/app/core/tenancy.py",
    "backend/app/models/task.py",
    "backend/app/models/trace.py",
    "backend/app/models/experiment.py",
    "backend/app/schemas/task.py",
    "backend/app/schemas/experiment.py",
    "backend/app/core/plugins/hooks.py",
]

REMOVE_PATTERNS = [
    r"^\s*print\(",
    r"^\s*breakpoint\(\)",
    r"^\s*import pdb",
    r"^\s*pdb\.",
    r"#\s*TODO",
    r"#\s*FIXME",
    r"#\s*HACK",
]

SECRET_RE = re.compile(
    r"""(password|secret|token|api_key|apikey)\s*=\s*['"][^'"]{4,}['"]""",
    re.IGNORECASE,
)


def clean_line(line):
    for pat in REMOVE_PATTERNS:
        if re.search(pat, line):
            return None
    line = line.replace("\t", "    ")
    line = SECRET_RE.sub(r'\1 = "REDACTED"', line)
    return line.rstrip()


def is_effective(line):
    s = line.strip()
    return bool(s) and not s.startswith("#")


def extract_file(filepath):
    path = Path(filepath)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw_lines = f.readlines()
    cleaned = []
    for line in raw_lines:
        result = clean_line(line.rstrip("\n"))
        if result is not None:
            cleaned.append(result)
    while len(cleaned) > 1 and cleaned[-1].strip() == "":
        cleaned.pop()
    return cleaned


def paginate(all_lines, lpp, total_pages):
    pages = []
    current_page = []
    eff_count = 0
    for line in all_lines:
        current_page.append(line)
        if is_effective(line):
            eff_count += 1
        if eff_count >= lpp:
            pages.append(current_page)
            current_page = []
            eff_count = 0
    if current_page and eff_count > 0:
        pages.append(current_page)
    if len(pages) > total_pages:
        half = total_pages // 2
        pages = pages[:half] + pages[-half:]
    return pages[:total_pages]


def write_output(pages, out_path):
    header = SOFTWARE_NAME + " \u6e90\u7a0b\u5e8f\u9274\u522b\u6750\u6599 " + VERSION
    sep = "-" * 60
    actual_total = len(pages)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for i, page in enumerate(pages, 1):
            f.write(header + "\n")
            f.write(sep + "\n")
            for line in page:
                f.write(line + "\n")
            f.write(sep + "\n")
            f.write("\u7b2c " + str(i) + " \u9875 / \u5171 " + str(actual_total) + " \u9875\n")
            f.write("\n")


def verify(out_path):
    with open(out_path, "r", encoding="utf-8") as f:
        content = f.read()
    report = {}
    page_marks = re.findall(r"^\u7b2c (\d+) \u9875", content, re.MULTILINE)
    report["total_pages"] = len(page_marks)
    report["pages_continuous"] = (
        [int(x) for x in page_marks] == list(range(1, len(page_marks) + 1))
    )
    report["file_count"] = len(re.findall(r"^# === File:", content, re.MULTILINE))
    report["file_size_bytes"] = out_path.stat().st_size
    leaks = re.findall(
        r"""(password|secret|token|api_key)\s*=\s*['"][^R'"][^'"]*['"]""",
        content, re.IGNORECASE,
    )
    report["secret_leaks"] = len(leaks)
    keywords = ["circuit", "ssrf", "topolog", "consistent", "sandbox",
                "lifecycle", "protocol", "judge", "middleware", "plugin"]
    report["keywords"] = {}
    for kw in keywords:
        report["keywords"][kw] = len(re.findall(kw, content, re.IGNORECASE))
    report["line_ending"] = "LF" if "\r\n" not in content else "CRLF"
    return report


def main():
    print("=" * 50)
    print("  " + SOFTWARE_NAME + " " + VERSION)
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 50)
    print()

    print("[Step 1/4] Scanning files...")
    found = []
    missing = []
    for f in FILES:
        if Path(f).exists():
            found.append(f)
            print("  [OK]      " + f)
        else:
            missing.append(f)
            print("  [MISSING] " + f)
    print()
    print("  Found: " + str(len(found)) + "/" + str(len(FILES)) + "  Missing: " + str(len(missing)))
    if missing:
        print("  WARNING: missing files listed above. Script continues with existing files.")
    print()

    print("[Step 2/4] Extracting code...")
    all_lines = []
    for f in found:
        all_lines.append("# === File: " + f + " ===")
        all_lines.append("# (c) 2026 " + SOFTWARE_NAME + " | Author: " + AUTHOR)
        all_lines.append("# " + "=" * 68)
        code = extract_file(f)
        all_lines.extend(code)
        all_lines.append("")
        eff = sum(1 for l in code if is_effective(l))
        print("  " + f + ": " + str(eff) + " effective lines")
    total_eff = sum(1 for l in all_lines if is_effective(l))
    print()
    print("  Total effective lines: " + str(total_eff))
    print()

    print("[Step 3/4] Paginating...")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    pages = paginate(all_lines, LINES_PER_PAGE, TOTAL_PAGES)
    final_path = OUTDIR / "source_code_60pages.txt"
    write_output(pages, final_path)
    print("  Pages: " + str(len(pages)))
    print("  Output: " + str(final_path))
    raw_path = OUTDIR / "code_raw.txt"
    with open(raw_path, "w", encoding="utf-8", newline="\n") as f:
        for line in all_lines:
            f.write(line + "\n")
    print("  Raw: " + str(raw_path))
    print()

    print("[Step 4/4] Verifying...")
    report = verify(final_path)
    print("  Pages: " + str(report["total_pages"]))
    print("  Continuous: " + str(report["pages_continuous"]))
    print("  File markers: " + str(report["file_count"]))
    print("  Size: " + str(report["file_size_bytes"]) + " bytes")
    print("  Secret leaks: " + str(report["secret_leaks"]))
    print("  Line ending: " + report["line_ending"])
    print()
    for kw, cnt in report["keywords"].items():
        mark = "OK" if cnt > 0 else "MISS"
        print("  [" + mark + "] " + kw + ": " + str(cnt))
    print()

    report_path = OUTDIR / "verify_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        for k, v in report.items():
            f.write(str(k) + ": " + str(v) + "\n")
    print("  Report: " + str(report_path))
    print()
    print("=" * 50)
    print("  DONE. Next: open " + str(final_path) + " and review.")
    print("=" * 50)


if __name__ == "__main__":
    main()
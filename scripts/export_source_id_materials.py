# -*- coding: utf-8 -*-
"""Export 60-page (50 lines/page) source identification materials for NCAC soft copyright."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOFTWARE = "AgentFlow-Eval Agent自动化评测工作台"
VERSION = "V1.0"
HEADER = f"// {SOFTWARE} {VERSION} - 李凯昕"
LINES_PER_PAGE = 50
# Page layout: 1 header line + 49 source lines = 50 lines/page
BODY_PER_PAGE = 49
HEAD_PAGES = 30
TAIL_PAGES = 30
OUT = ROOT / "docs" / "soft-copyright" / "generated" / "源程序鉴别材料_60页_李凯昕.txt"

FRONT_FILES = [
    "backend/app/main.py",
    "backend/app/config.py",
    "backend/app/api/v1/router.py",
    "backend/app/core/security.py",
    "backend/app/core/middleware.py",
    "backend/app/core/dependencies.py",
    "backend/app/core/tenancy.py",
    "backend/app/models/base.py",
    "backend/app/models/task.py",
    "backend/app/models/test_suite.py",
    "backend/app/models/trace.py",
    "backend/app/models/metric_score.py",
    "backend/app/models/audit_log.py",
    "backend/app/schemas/task.py",
    "backend/app/schemas/trace.py",
    "backend/app/utils/exceptions.py",
    "backend/app/utils/logger.py",
    "backend/app/api/v1/endpoints/tasks.py",
    "backend/app/api/v1/endpoints/settings.py",
    "backend/app/api/v1/endpoints/tools.py",
    "backend/app/api/v1/endpoints/ws.py",
    "backend/app/api/v1/endpoints/audit.py",
    "frontend/src/main.tsx",
    "frontend/src/App.tsx",
    "frontend/src/router/index.tsx",
    "frontend/src/api/client.ts",
    "frontend/src/api/endpoints/tasks.ts",
    "frontend/src/stores/useTaskStore.ts",
    "frontend/src/hooks/useTasks.ts",
]

TAIL_FILES = [
    "backend/app/core/agent_runner/base.py",
    "backend/app/core/agent_runner/openai_runner.py",
    "backend/app/core/agent_runner/tool_sandbox.py",
    "backend/app/core/agent_runner/parser.py",
    "backend/app/core/judge_engine/base.py",
    "backend/app/core/judge_engine/metrics.py",
    "backend/app/core/judge_engine/llm_judge.py",
    "backend/app/core/celery_app/celery.py",
    "backend/app/core/celery_app/tasks.py",
    "backend/app/core/events.py",
    "backend/app/core/ws_hub.py",
    "backend/app/core/audit.py",
    "backend/app/api/v1/endpoints/traces.py",
    "backend/app/api/v1/endpoints/reports.py",
    "backend/app/utils/cost.py",
    "frontend/src/components/TraceFlow/TraceFlowChart.tsx",
    "frontend/src/components/TraceFlow/ScoreCard.tsx",
    "frontend/src/components/TraceFlow/StepLogPanel.tsx",
    "frontend/src/pages/tasks/detail.tsx",
    "frontend/src/pages/tasks/create.tsx",
    "frontend/src/pages/tasks/index.tsx",
    "frontend/src/pages/reports/ReportDetail.tsx",
]


def desensitize(line: str) -> str:
    s = line
    s = re.sub(
        r"(api[_-]?key\s*=\s*)(['\"]?)[^'\"\s,)]+",
        r"\1\2YOUR_API_KEY_HERE\2",
        s,
        flags=re.I,
    )
    s = re.sub(r"(OPENAI_API_KEY\s*[=:]\s*)(\S+)", r"\1YOUR_API_KEY_HERE", s)
    s = re.sub(r"(API_KEYS\s*[=:]\s*)(\S+)", r"\1YOUR_API_KEYS_HERE", s)
    s = re.sub(
        r"(password\s*=\s*)(['\"]?)[^'\"\s,)]+",
        r"\1\2***\2",
        s,
        flags=re.I,
    )
    s = re.sub(r"sk-[A-Za-z0-9]{8,}", "YOUR_API_KEY_HERE", s)
    s = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b", "***", s)
    s = re.sub(r"https?://127\.0\.0\.1[^\s'\"]*", "https://YOUR_HOST_HERE", s)
    s = re.sub(r"https?://localhost[^\s'\"]*", "https://YOUR_HOST_HERE", s)
    s = re.sub(
        r"https?://[a-zA-Z0-9._\-]+(?::\d+)?(?:/[^\s'\"]*)?",
        "https://YOUR_HOST_HERE",
        s,
    )
    s = re.sub(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        "YOUR_EMAIL_HERE",
        s,
    )
    return s


def is_drop_line(line: str) -> bool:
    t = line.strip()
    if t.startswith("#!"):
        return True
    if re.search(r"\(c\)\s*20\d\d", t, re.I):
        return True
    if re.match(r"^#\s*\(c\)", t, re.I):
        return True
    if re.search(r"(微信|QQ群|电话|手机号|mailto:)", t, re.I):
        return True
    if re.match(r"^(print\(|console\.log\(|debugger\b)", t):
        return True
    return False


def load_file(rel: str) -> list[str]:
    path = ROOT / rel
    if not path.exists():
        return []
    lines: list[str] = [f"// FILE: {rel}"]
    text = path.read_text(encoding="utf-8-sig", errors="replace")  # strip BOM
    for raw in text.splitlines():
        line = raw.rstrip().replace("\ufeff", "")
        if is_drop_line(line):
            continue
        lines.append(desensitize(line))
    return lines


def compact(lines: list[str]) -> list[str]:
    out: list[str] = []
    blank = 0
    for ln in lines:
        if not ln.strip():
            blank += 1
            if blank <= 1:
                out.append("")
            continue
        blank = 0
        out.append(ln)
    return out


def gather(files: list[str], need: int) -> list[str]:
    buf: list[str] = []
    for rel in files:
        buf.extend(load_file(rel))
        buf = compact(buf)
        if len(buf) >= need:
            break
    if len(buf) < need:
        raise SystemExit(f"Not enough lines: have {len(buf)}, need {need}")
    return buf[:need]


def paginate(body_lines: list[str], pages: int) -> list[str]:
    """Return flat list of lines for `pages` pages (50 lines each)."""
    result: list[str] = []
    for p in range(pages):
        chunk = body_lines[p * BODY_PER_PAGE : (p + 1) * BODY_PER_PAGE]
        if len(chunk) < BODY_PER_PAGE:
            chunk = chunk + [""] * (BODY_PER_PAGE - len(chunk))
        page = [HEADER] + chunk
        assert len(page) == LINES_PER_PAGE
        result.extend(page)
    return result


def main() -> None:
    need = HEAD_PAGES * BODY_PER_PAGE
    front = gather(FRONT_FILES, need)
    tail = gather(TAIL_FILES, need)
    all_lines = paginate(front, HEAD_PAGES) + paginate(tail, TAIL_PAGES)
    assert len(all_lines) == 60 * 50
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    # also write split first/last 30 for convenience
    mid = 30 * 50
    (OUT.parent / "源程序鉴别材料_前30页.txt").write_text(
        "\n".join(all_lines[:mid]) + "\n", encoding="utf-8"
    )
    (OUT.parent / "源程序鉴别材料_后30页.txt").write_text(
        "\n".join(all_lines[mid:]) + "\n", encoding="utf-8"
    )
    print("OK", OUT)
    print("total lines", len(all_lines))
    print("pages", len(all_lines) // 50)


if __name__ == "__main__":
    main()

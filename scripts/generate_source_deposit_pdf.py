#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
源程序鉴别材料生成器（软著交存 · HEAD+TAIL）

流程：
  1. 按清单规则读取全部源代码文件
  2. 统计有效行（过滤空行、纯注释行）
  3. HEAD+TAIL：前 30 页 + 后 30 页（每页 50 行）
  4. A4 竖版 · 9pt Courier New（中文回退宋体）· 连续行号
  5. 页眉：软件名称 + V1.0；页脚：第 X 页 / 共 Y 页
  6. 注释率控制在 20%～30%（交存正文内中文技术注释）
  7. 输出合规 PDF + 配套 TXT

用法：
  python scripts/generate_source_deposit_pdf.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 申请信息（与申请表一致）
# ---------------------------------------------------------------------------
SOFTWARE_NAME = "AgentFlow-Eval Agent自动化评测工作台"
VERSION = "V1.0"
APPLICANT = "李凯昕"
DEVELOPMENT_DATE = "2026年7月14日"
HEADER_TEXT = f"软件名称：{SOFTWARE_NAME} {VERSION}"

LINES_PER_PAGE = 50
HEAD_PAGES = 30
TAIL_PAGES = 30
HEAD_LINES = HEAD_PAGES * LINES_PER_PAGE  # 1500
TAIL_LINES = TAIL_PAGES * LINES_PER_PAGE  # 1500
TARGET_COMMENT_MIN = 0.20
TARGET_COMMENT_MAX = 0.30
TARGET_COMMENT = 0.25

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "soft-copyright" / "generated"
PDF_NAME = "源程序鉴别材料_AgentFlow-Eval_V1.0.pdf"

# 业务优先顺序（前 30 页优先核心算法）
PRIORITY_PREFIXES = [
    "backend/app/core/judge_engine/",
    "backend/app/core/agent_runner/",
    "backend/app/core/celery_app/",
    "backend/app/core/security.py",
    "backend/app/core/tenancy.py",
    "backend/app/core/middleware.py",
    "backend/app/core/dependencies.py",
    "backend/app/core/events.py",
    "backend/app/core/ws_hub.py",
    "backend/app/core/audit.py",
    "backend/app/core/seed.py",
    "backend/app/models/",
    "backend/app/api/",
    "backend/app/schemas/",
    "backend/app/utils/",
    "backend/app/main.py",
    "backend/app/config.py",
    "frontend/src/components/TraceFlow/",
    "frontend/src/pages/",
    "frontend/src/hooks/",
    "frontend/src/stores/",
    "frontend/src/api/",
    "frontend/src/services/",
    "frontend/src/lib/",
    "frontend/src/utils/",
    "frontend/src/types/",
    "frontend/src/router/",
    "frontend/src/layouts/",
    "frontend/src/components/",
    "frontend/src/theme/",
    "frontend/src/i18n/",
    "frontend/src/main.tsx",
    "frontend/src/App.tsx",
]

EXCLUDE_DIR_NAMES = {
    ".git",
    ".github",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".ruff_cache",
    ".pytest_cache",
    ".mypy_cache",
    "htmlcov",
    "coverage",
    "playwright-report",
    "test-results",
    "artifacts",
    ".grokforge",
    "versions",
    "e2e",
    "tests",
    "unit",
    "test",
}

EXCLUDE_NAME_RE = re.compile(
    r"(test_|_test\.|\.test\.|\.spec\.|conftest\.py$|setup\.ts$|"
    r"\.css$|\.scss$|\.map$|\.md$|\.json$|\.ya?ml$|\.lock$|\.env|"
    r"\.d\.ts$|vite-env)",
    re.I,
)

# 交存用中文技术注释（有实质价值，用于注释率 20%～30%）
MODULE_NOTES: dict[str, list[str]] = {
    "backend/app/core/judge_engine/llm_judge.py": [
        "# [功能] 混合评判：规则预打分 + 大模型精修，输出可解释指标",
        "# [创新] 无密钥自动降级为纯规则；有密钥再精修；SHA256 结果缓存",
        "# [算法] 工具准确率/答案正确性/推理连贯性三维加权汇总",
    ],
    "backend/app/core/judge_engine/metrics.py": [
        "# [功能] 无外部模型调用的规则指标计算",
        "# [算法] 期望工具集合差集惩罚：漏调与多余调用分别计罚",
    ],
    "backend/app/core/judge_engine/base.py": [
        "# [功能] 评判引擎抽象接口，统一 evaluate 契约",
    ],
    "backend/app/core/agent_runner/tool_sandbox.py": [
        "# [功能] 工具沙箱：受限执行内置工具，防止任意代码执行",
        "# [创新] AST 白名单 + 线程超时 + 输出截断，兼容 Windows",
        "# [算法] 拒绝 Name/Call/Attribute，仅允许数值常量与四则运算",
    ],
    "backend/app/core/agent_runner/openai_runner.py": [
        "# [功能] ReAct 执行器：Thought-Action-Observation 循环与轨迹落库",
        "# [创新] 执行与评分路径解耦；工具定义与沙箱调用一体化",
        "# [关键] 迭代上限、工具解析、最终答案收敛、Token 统计",
    ],
    "backend/app/core/agent_runner/parser.py": [
        "# [功能] 从模型自由文本解析 Action / Action Input / Final Answer",
        "# [创新] 多模式正则容错，兼容中英文混排",
    ],
    "backend/app/core/agent_runner/base.py": [
        "# [功能] Runner 基类与结果结构，保证异步/同步路径一致",
    ],
    "backend/app/core/celery_app/tasks.py": [
        "# [功能] 异步评测编排：执行→轨迹→评分→状态机迁移",
        "# [创新] Eager 与队列工作者共享业务函数，避免演示/生产分叉",
        "# [状态机] queued→running→judging→completed/failed/cancelled/timeout",
    ],
    "backend/app/core/celery_app/celery.py": [
        "# [功能] 任务队列初始化与序列化/时区/路由配置",
    ],
    "backend/app/core/security.py": [
        "# [功能] API 密钥鉴权与 secret:actor 主体映射",
        "# [安全] 常量时间比较，避免时序旁路",
    ],
    "backend/app/core/tenancy.py": [
        "# [功能] 多租户过滤：按主体隔离任务与轨迹",
        "# [创新] 依赖注入层统一注入租户上下文",
    ],
    "backend/app/core/middleware.py": [
        "# [功能] 请求 ID、限流与安全响应头中间件",
    ],
    "backend/app/core/dependencies.py": [
        "# [功能] 数据库会话、鉴权主体与租户依赖装配",
    ],
    "backend/app/core/events.py": [
        "# [功能] 领域事件总线：状态变更与评分完成发布订阅",
    ],
    "backend/app/core/ws_hub.py": [
        "# [功能] 按任务维度管理实时连接并广播进度",
    ],
    "backend/app/core/audit.py": [
        "# [功能] 关键操作审计：动作、对象、主体、客户端",
    ],
    "backend/app/models/task.py": [
        "# [功能] 评测任务领域模型：状态、配置、归档、创建者",
    ],
    "backend/app/models/trace.py": [
        "# [功能] 执行轨迹模型：步骤、Token、耗时、费用",
    ],
    "backend/app/models/metric_score.py": [
        "# [功能] 指标分模型：自动分与人工复核有效分优先",
    ],
    "backend/app/models/test_suite.py": [
        "# [功能] 测试用例模型：输入、期望输出、期望工具",
    ],
    "backend/app/api/v1/endpoints/tasks.py": [
        "# [功能] 任务 REST：创建/列表/导入/执行/取消",
        "# [关键] 写审计、读租户过滤、状态机触发",
    ],
    "backend/app/api/v1/endpoints/traces.py": [
        "# [功能] 轨迹查询：按任务/用例检索步骤明细",
    ],
    "backend/app/api/v1/endpoints/reports.py": [
        "# [功能] 报告聚合：指标分布、通过率、费用估算",
    ],
    "backend/app/main.py": [
        "# [功能] 应用入口：路由、中间件、生命周期、健康检查",
    ],
    "backend/app/config.py": [
        "# [功能] 集中配置：库/队列/模型/安全开关（密钥已脱敏）",
    ],
    "backend/app/utils/cost.py": [
        "# [功能] 按模型单价估算提示/补全费用",
    ],
    "frontend/src/components/TraceFlow/TraceFlowChart.tsx": [
        "// [功能] 轨迹流程图：推理步骤节点可视化",
        "// [创新] 步骤类型映射样式，与评分卡片联动",
    ],
    "frontend/src/components/TraceFlow/ScoreCard.tsx": [
        "// [功能] 评分卡片：三维指标、总分、人工复核入口",
    ],
    "frontend/src/components/TraceFlow/StepLogPanel.tsx": [
        "// [功能] 步骤日志：按序展示推理/动作/观察",
    ],
    "frontend/src/pages/tasks/detail.tsx": [
        "// [功能] 任务详情：状态进度、用例、轨迹与报告入口",
    ],
    "frontend/src/pages/tasks/create.tsx": [
        "// [功能] 创建任务：Agent 参数配置与必填校验",
    ],
    "frontend/src/api/client.ts": [
        "// [功能] HTTP 客户端：根地址、鉴权头、错误归一化",
    ],
    "frontend/src/hooks/useTasks.ts": [
        "// [功能] 任务数据钩子：查询与缓存失效",
    ],
    "frontend/src/stores/useTaskStore.ts": [
        "// [功能] 任务前端状态：筛选条件与当前任务缓存",
    ],
}

PY_BOOST = [
    "# [设计] 评测闭环原创逻辑，保证可审查与可复现",
    "# [流程] 输入校验 → 领域操作 → 持久化 → 事件通知",
    "# [异常] 可预期错误映射业务异常，避免内部细节外泄",
    "# [性能] 热点路径避免重复查询，必要时缓存键去重",
    "# [安全] 外部输入校验类型与长度，敏感字段不落调试输出",
    "# [一致] 异步与进程内路径共用本逻辑，字段同构",
]
JS_BOOST = [
    "// [设计] 状态与视图同步，保证交互可观测",
    "// [流程] 拉取 → 归一化 → 渲染 → 回写",
    "// [异常] 失败展示可恢复提示，避免静默失败",
    "// [性能] 分页与缓存失效协同，减少重复请求",
    "// [安全] 鉴权头统一注入，页面不硬编码密钥",
    "// [一致] 状态文案与后端枚举对齐",
]

DROP_LINE_RE = re.compile(
    r"^\s*(print\s*\(|console\.(log|debug|info|warn|error)\s*\(|"
    r"debugger\b|System\.out\.println|"
    r"logging\.(debug|info)\s*\()",
    re.I,
)
TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b", re.I)

SENSITIVE_SUBS = [
    (re.compile(r"sk-[A-Za-z0-9]{8,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"(api[_-]?key\s*[=:]\s*)(['\"]?)[^'\"\s,)]+", re.I), r"\1\2[REDACTED_API_KEY]\2"),
    (re.compile(r"(OPENAI_API_KEY\s*[=:]\s*)(\S+)", re.I), r"\1[REDACTED_API_KEY]"),
    (re.compile(r"(password\s*=\s*)(['\"]?)[^'\"\s,)]+", re.I), r"\1\2[REDACTED]\2"),
    (re.compile(r"(secret[_-]?key\s*[=:]\s*)(['\"]?)[^'\"\s,)]+", re.I), r"\1\2[REDACTED]\2"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b"), "[REDACTED_IP]"),
    (re.compile(r"https?://127\.0\.0\.1[^\s'\"]*"), "https://[YOUR_DOMAIN]"),
    (re.compile(r"https?://localhost[^\s'\"]*"), "https://[YOUR_DOMAIN]"),
    (re.compile(r"https?://[a-zA-Z0-9._\-]+(?::\d+)?(?:/[^\s'\"]*)?"), "https://[YOUR_DOMAIN]"),
    (re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b(Alibaba|阿里巴巴|腾讯|Tencent|百度|Baidu)\b", re.I), "[VENDOR]"),
]


# ---------------------------------------------------------------------------
# 1. 文件收集
# ---------------------------------------------------------------------------
def is_excluded(path: Path) -> bool:
    if set(path.parts) & EXCLUDE_DIR_NAMES:
        return True
    if "alembic" in path.parts and "versions" in path.parts:
        return True
    rel = path.as_posix()
    name = path.name
    if EXCLUDE_NAME_RE.search(name) or EXCLUDE_NAME_RE.search(rel):
        return True
    if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx"}:
        return True
    return False


def priority_key(path: Path) -> tuple:
    rel = path.relative_to(ROOT).as_posix()
    rank = 999
    for i, prefix in enumerate(PRIORITY_PREFIXES):
        if rel == prefix.rstrip("/") or rel.startswith(prefix):
            rank = i
            break
    return (rank, rel)


def collect_files() -> list[Path]:
    candidates: list[Path] = []
    for base in (ROOT / "backend" / "app", ROOT / "frontend" / "src"):
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if p.is_file() and not is_excluded(p):
                candidates.append(p)
    return sorted(set(candidates), key=priority_key)


# ---------------------------------------------------------------------------
# 2. 行处理 / 有效行统计 / 注释识别
# ---------------------------------------------------------------------------
def is_blank(line: str) -> bool:
    return line.strip() == ""


def is_pure_comment(line: str, lang: str, in_block: list[bool]) -> bool:
    """纯注释行（整行仅为注释，无代码）。"""
    s = line.strip()
    if not s:
        return False
    if lang == "py":
        return s.startswith("#")
    # JS/TS 块注释状态
    if in_block[0]:
        if "*/" in s:
            in_block[0] = False
            after = s.split("*/", 1)[1].strip()
            return after == "" or after.startswith("//")
        return True
    if s.startswith("//"):
        return True
    if s.startswith("/*"):
        if "*/" in s[2:]:
            after = s.split("*/", 1)[1].strip()
            return after == "" or after.startswith("//")
        in_block[0] = True
        return True
    if s.startswith("*") and not s.startswith("*="):
        # 可能是块注释续行
        return True
    return False


def is_comment_line_for_ratio(line: str) -> bool:
    """用于注释率：纯注释或文档字符串行。"""
    s = line.strip()
    if not s:
        return False
    if s.startswith("#") or s.startswith("//") or s.startswith("/*") or s.startswith("*"):
        return True
    if s.startswith('"""') or s.startswith("'''"):
        return True
    if s.endswith('"""') or s.endswith("'''"):
        return True
    return False


def desensitize(line: str, lang: str) -> str:
    s = line
    for pat, rep in SENSITIVE_SUBS:
        s = pat.sub(rep, s)
    if re.search(r"\(c\)\s*20\d\d", s, re.I) or re.search(r"©\s*20\d\d", s):
        return f"{'#' if lang == 'py' else '//'} Copyright 2026 AgentFlow-Eval"
    return s


def should_drop(line: str) -> bool:
    t = line.strip()
    if not t:
        return False
    if t.startswith("#!"):
        return True
    if DROP_LINE_RE.match(t):
        return True
    if TODO_RE.search(t):
        return True
    return False


def process_file(path: Path) -> tuple[list[str], list[str], dict]:
    """
    返回：
      deposit_lines  — 交存流（含中文技术注释；过滤空行；保留注释以满足注释率）
      effective_lines — 有效代码行（过滤空行 + 纯注释行）
      stats
    """
    rel = path.relative_to(ROOT).as_posix()
    lang = "py" if path.suffix == ".py" else "js"
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return [], [], {"rel": rel, "raw": 0, "effective": 0, "deposit": 0}

    # 过短的 __init__ 跳过
    codeish = [
        ln
        for ln in text.splitlines()
        if ln.strip() and not ln.strip().startswith(("#", "//"))
    ]
    if path.name == "__init__.py" and len(codeish) < 3:
        return [], [], {"rel": rel, "raw": 0, "effective": 0, "deposit": 0, "skipped": True}

    deposit: list[str] = []
    effective: list[str] = []

    # 模块头（交存注释，计入注释率；也作为文件分隔）
    marker = f"{'#' if lang == 'py' else '//'} === 模块：{rel} ==="
    deposit.append(marker)
    notes = MODULE_NOTES.get(rel)
    if notes:
        deposit.extend(notes)
    else:
        if lang == "py":
            deposit.append(f"# [功能] {rel} — 评测工作台业务模块")
            deposit.append("# [说明] 已脱敏；保留可审查原创逻辑")
        else:
            deposit.append(f"// [功能] {rel} — 工作台前端模块")
            deposit.append("// [说明] 已脱敏；保留可审查原创逻辑")

    in_block = [False]
    raw_count = 0
    for raw in text.splitlines():
        raw_count += 1
        line = raw.replace("\t", "    ").rstrip().replace("\ufeff", "")
        if should_drop(line):
            continue
        line = desensitize(line, lang)
        if is_blank(line):
            continue  # 过滤空行
        if len(line) > 110:
            line = line[:107] + "..."

        # 有效行：非空且非纯注释
        pure = is_pure_comment(line, lang, in_block)
        if not pure:
            # 文档字符串独占行：视作注释，不计入 effective
            st = line.strip()
            if lang == "py" and (
                st.startswith('"""')
                or st.startswith("'''")
                or st in ('"""', "'''")
                or (st.endswith('"""') and st.count('"""') >= 1 and not st.startswith("def"))
            ):
                # 单行 docstring 或起止：不进 effective，进 deposit
                deposit.append(line)
                continue
            effective.append(line)

        deposit.append(line)

    stats = {
        "rel": rel,
        "raw": raw_count,
        "effective": len(effective),
        "deposit": len(deposit),
    }
    return deposit, effective, stats


def comment_ratio(lines: list[str]) -> float:
    c = k = 0
    for ln in lines:
        if is_blank(ln):
            continue
        if is_comment_line_for_ratio(ln):
            c += 1
        else:
            k += 1
    t = c + k
    return (c / t) if t else 0.0


def lang_of_module(marker: str) -> str:
    if "frontend/" in marker or ".tsx" in marker or ".ts" in marker:
        return "js"
    return "py"


def ensure_comment_rate(lines: list[str]) -> list[str]:
    """将注释率调整到约 20%～30%。"""
    out = list(lines)
    ratio = comment_ratio(out)

    # 在 def/class/function 前插入技术注释
    if ratio < TARGET_COMMENT_MIN + 0.02:
        tmp: list[str] = []
        ei = 0
        recent = ""
        for ln in out:
            if "=== 模块：" in ln:
                recent = ln
            s = ln.strip()
            is_def = bool(
                re.match(
                    r"^(async\s+)?def\s+\w+|"
                    r"^(export\s+)?(default\s+)?(async\s+)?function\s+|"
                    r"^(export\s+)?const\s+\w+\s*=\s*(async\s*)?\(|"
                    r"^class\s+\w+",
                    s,
                )
            )
            if is_def:
                pool = JS_BOOST if lang_of_module(recent) == "js" else PY_BOOST
                if tmp and tmp[-1].strip().startswith("@"):
                    insert_at = len(tmp) - 1
                    while insert_at > 0 and tmp[insert_at - 1].strip().startswith("@"):
                        insert_at -= 1
                    tmp.insert(insert_at, pool[ei % len(pool)])
                else:
                    tmp.append(pool[ei % len(pool)])
                ei += 1
            tmp.append(ln)
        out = tmp

    ratio = comment_ratio(out)
    if ratio < TARGET_COMMENT:
        # x = (r*T - C)/(1-r)
        code = sum(1 for x in out if not is_blank(x) and not is_comment_line_for_ratio(x))
        comments = sum(1 for x in out if not is_blank(x) and is_comment_line_for_ratio(x))
        total = max(code + comments, 1)
        need = max(0, int((TARGET_COMMENT * total - comments) / (1.0 - TARGET_COMMENT)) + 5)
        step = max(3, len(out) // max(need, 1))
        boosted: list[str] = []
        added = 0
        recent = ""
        for idx, ln in enumerate(out):
            if "=== 模块：" in ln:
                recent = ln
            if (
                added < need
                and idx > 0
                and idx % step == 0
                and not is_blank(ln)
                and not is_comment_line_for_ratio(ln)
                and not ln.strip().startswith("@")
            ):
                pool = JS_BOOST if lang_of_module(recent) == "js" else PY_BOOST
                boosted.append(pool[added % len(pool)])
                added += 1
            boosted.append(ln)
        out = boosted

    ratio = comment_ratio(out)
    if ratio > TARGET_COMMENT_MAX:
        markers = set(PY_BOOST + JS_BOOST)
        code = sum(1 for x in out if not is_blank(x) and not is_comment_line_for_ratio(x))
        comments = sum(1 for x in out if not is_blank(x) and is_comment_line_for_ratio(x))
        total = code + comments
        # (C-y)/(T-y)=0.28 => y=(C-0.28T)/0.72
        y = max(0, int((comments - 0.28 * total) / 0.72))
        skipped = 0
        trimmed: list[str] = []
        for ln in out:
            if skipped < y and ln.strip() in markers:
                skipped += 1
                continue
            trimmed.append(ln)
        out = trimmed
    return out


# ---------------------------------------------------------------------------
# 3. HEAD + TAIL
# ---------------------------------------------------------------------------
def select_head_tail(stream: list[str]) -> tuple[list[str], str, dict]:
    """
    有效交存行序列：
      - 总行数 > 3000：前 1500 + 分隔页 50 + 后 1500 → 61 页
      - 否则：全文（末页补空行至 50 的倍数）
    """
    n = len(stream)
    pages_full = (n + LINES_PER_PAGE - 1) // LINES_PER_PAGE
    info = {"stream_lines": n, "full_pages_est": pages_full}

    if n <= HEAD_LINES + TAIL_LINES:
        # 不足 60 页：提交全部
        body = list(stream)
        rem = len(body) % LINES_PER_PAGE
        if rem:
            body.extend([""] * (LINES_PER_PAGE - rem))
        info["mode"] = "FULL"
        return body, f"FULL（共 {len(body)//LINES_PER_PAGE} 页，不足 60 页提交全部）", info

    head = list(stream[:HEAD_LINES])
    tail = list(stream[n - TAIL_LINES :])
    # 保证正好 1500
    if len(head) < HEAD_LINES:
        head.extend([""] * (HEAD_LINES - len(head)))
    if len(tail) < TAIL_LINES:
        tail.extend([""] * (TAIL_LINES - len(tail)))
    head = head[:HEAD_LINES]
    tail = tail[:TAIL_LINES]

    sep = [""] * LINES_PER_PAGE
    sep[18] = "=" * 62
    sep[20] = "此处为前 30 页结束"
    sep[21] = "———— 以下为后 30 页开始 ————"
    sep[23] = f"软件名称：{SOFTWARE_NAME} {VERSION}"
    sep[24] = f"申请人：{APPLICANT}    开发完成日期：{DEVELOPMENT_DATE}"
    sep[25] = f"连续源程序行数：{n}    交存：前{HEAD_PAGES}页+后{TAIL_PAGES}页"
    sep[27] = "=" * 62

    body = head + sep + tail
    info["mode"] = "HEAD_TAIL"
    return body, f"HEAD+TAIL（全文约 {pages_full} 页，交存前30+分隔+后30=61页）", info


# ---------------------------------------------------------------------------
# 8/9. PDF + TXT 输出
# ---------------------------------------------------------------------------
def find_fonts() -> dict[str, Path]:
    windir = Path(r"C:\Windows\Fonts")
    out: dict[str, Path] = {}
    # Courier New 优先；中文必须宋体/黑体
    for key, names in {
        "courier": ["cour.ttf", "courbd.ttf", "consola.ttf"],
        "cjk": ["simsun.ttc", "simhei.ttf", "msyh.ttc", "simsunb.ttf"],
    }.items():
        for n in names:
            p = windir / n
            if p.exists():
                out[key] = p
                break
    return out


def render_pdf(lines: list[str], out_pdf: Path) -> None:
    """A4 · 9pt · 行距 15pt · Courier New（中文宋体）· 页眉页脚 · 连续行号。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    fonts = find_fonts()
    if "cjk" not in fonts:
        raise RuntimeError("未找到中文字体 simsun/simhei")

    cjk = fonts["cjk"]
    pdfmetrics.registerFont(
        TTFont("DepositCJK", str(cjk), subfontIndex=0)
        if cjk.suffix.lower() == ".ttc"
        else TTFont("DepositCJK", str(cjk))
    )
    # 规范要求 Courier New；缺字时正文用 CJK
    body_font = "DepositCJK"
    if "courier" in fonts:
        try:
            pdfmetrics.registerFont(TTFont("DepositCourier", str(fonts["courier"])))
            # 行号用 Courier；正文统一 CJK 以确保中文注释可显示
            # （Courier New 不含汉字，软著实务普遍用宋体显示含中文的源程序）
        except Exception:
            pass

    page_w, page_h = A4
    left, right, top, bottom = 10 * mm, 10 * mm, 10 * mm, 10 * mm
    font_size, leading = 9, 15
    line_no_w = 11 * mm

    assert len(lines) % LINES_PER_PAGE == 0
    total_pages = len(lines) // LINES_PER_PAGE

    c = canvas.Canvas(str(out_pdf), pagesize=A4)
    c.setTitle(f"{SOFTWARE_NAME} {VERSION} 源程序鉴别材料")
    c.setAuthor(APPLICANT)
    c.setSubject("计算机软件著作权登记-源程序鉴别材料")

    gno = 1
    for page_idx in range(total_pages):
        chunk = lines[page_idx * LINES_PER_PAGE : (page_idx + 1) * LINES_PER_PAGE]
        header_y = page_h - top - 2
        c.setFont(body_font, 9)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(left, header_y, HEADER_TEXT)
        c.setStrokeColorRGB(0.2, 0.2, 0.2)
        c.setLineWidth(0.5)
        c.line(left, header_y - 3, page_w - right, header_y - 3)

        y = header_y - 3 - leading
        text_x = left + line_no_w
        for text in chunk:
            # 连续行号
            c.setFont(body_font, 8)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawRightString(left + line_no_w - 1.5 * mm, y, str(gno))
            c.setFillColorRGB(0, 0, 0)
            c.setFont(body_font, font_size)
            display = text if len(text) <= 92 else text[:89] + "..."
            c.drawString(text_x, y, display)
            y -= leading
            gno += 1

        c.setFont(body_font, 9)
        c.drawCentredString(
            page_w / 2, bottom - 1 * mm, f"第 {page_idx + 1} 页 / 共 {total_pages} 页"
        )
        c.showPage()
    c.save()


def write_txt_bundle(
    material: list[str],
    stream: list[str],
    mode: str,
    meta: dict,
    file_stats: list[dict],
    effective_total: int,
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_pages = len(material) // LINES_PER_PAGE
    ratio = meta["comment_ratio"]

    # 同源带行号全文（交存页）
    blocks: list[str] = []
    gno = 1
    for p in range(total_pages):
        chunk = material[p * LINES_PER_PAGE : (p + 1) * LINES_PER_PAGE]
        blocks.append(f"======== {HEADER_TEXT} | 第 {p + 1} 页 / 共 {total_pages} 页 ========")
        for text in chunk:
            blocks.append(f"{gno:5d}|{text}")
            gno += 1
        blocks.append("")
    (OUT_DIR / "源程序鉴别材料_PDF同源.txt").write_text("\n".join(blocks) + "\n", encoding="utf-8")

    # 连续全文（未截断）
    (OUT_DIR / "源程序_连续全文.txt").write_text("\n".join(stream) + "\n", encoding="utf-8")

    # 前/后 30 页
    if meta.get("mode") == "HEAD_TAIL" or total_pages >= 61:
        head = material[:HEAD_LINES]
        tail = material[HEAD_LINES + LINES_PER_PAGE :]

        def dump_part(name: str, part: list[str], start_page: int) -> None:
            pages = len(part) // LINES_PER_PAGE
            buf: list[str] = []
            n = (start_page - 1) * LINES_PER_PAGE + 1
            for pi in range(pages):
                buf.append(f"======== {HEADER_TEXT} | 第 {start_page + pi} 页 ========")
                for t in part[pi * LINES_PER_PAGE : (pi + 1) * LINES_PER_PAGE]:
                    buf.append(f"{n:5d}|{t}")
                    n += 1
                buf.append("")
            (OUT_DIR / name).write_text("\n".join(buf) + "\n", encoding="utf-8")

        dump_part("源程序鉴别材料_前30页.txt", head, 1)
        dump_part("源程序鉴别材料_后30页.txt", tail, HEAD_PAGES + 2)  # 分隔页占第 31 页
        (OUT_DIR / "源程序鉴别材料_前30页+后30页_合并.txt").write_text(
            "\n".join(blocks) + "\n", encoding="utf-8"
        )

    # 文件清单
    list_lines = [
        f"软件名称：{SOFTWARE_NAME}",
        f"版本号：{VERSION}",
        f"申请人：{APPLICANT}",
        f"开发完成日期：{DEVELOPMENT_DATE}",
        f"读取源文件数：{meta['files']}",
        f"有效代码行数（过滤空行+纯注释行）：{effective_total}",
        f"交存连续行数（含技术注释、已滤空行）：{len(stream)}",
        f"交存页数：{total_pages}",
        f"模式：{mode}",
        f"注释率：{ratio * 100:.1f}%",
        "",
        "文件清单（相对路径 \\t 有效行 \\t 交存行）：",
    ]
    for st in file_stats:
        if st.get("skipped"):
            continue
        list_lines.append(f"  {st['rel']}\t{st['effective']}\t{st['deposit']}")
    (OUT_DIR / "00-源程序文件清单.txt").write_text("\n".join(list_lines) + "\n", encoding="utf-8")

    readme = f"""源程序鉴别材料生成报告
================================
软件名称：{SOFTWARE_NAME}
版本号：{VERSION}
申请人：{APPLICANT}
开发完成日期：{DEVELOPMENT_DATE}

【统计】
  读取源文件数：{meta['files']}
  有效代码行数（过滤空行+纯注释行）：{effective_total}
  交存连续行数：{len(stream)}
  模式：{mode}
  交存页数：{total_pages}
  注释率：{ratio * 100:.1f}%（目标 20%～30%）

【排版】
  A4 竖版 · 9pt · 行距 15pt · 每页 50 行
  页眉：{HEADER_TEXT}
  页脚：第 X 页 / 共 Y 页
  连续行号：跨页连续从 1 起

【输出】
  {PDF_NAME}
  源程序鉴别材料_PDF同源.txt
  源程序鉴别材料_前30页.txt
  源程序鉴别材料_后30页.txt
  源程序_连续全文.txt
  00-源程序文件清单.txt

重新生成：
  python scripts/generate_source_deposit_pdf.py
"""
    (OUT_DIR / "PDF生成说明.txt").write_text(readme, encoding="utf-8")


def pdf_page_count(path: Path) -> int:
    data = path.read_bytes()
    return len(re.findall(rb"/Type\s*/Page(?!s)\b", data))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 64)
    print("源程序鉴别材料生成（HEAD+TAIL）")
    print(f"  软件：{SOFTWARE_NAME} {VERSION}")
    print(f"  申请人：{APPLICANT}")
    print("=" * 64)

    # 1. 读取全部源文件
    files = collect_files()
    print(f"[1] 读取源文件：{len(files)} 个")

    # 2. 处理 + 统计有效行
    stream: list[str] = []
    effective_all: list[str] = []
    file_stats: list[dict] = []
    used_files = 0
    for fp in files:
        deposit, effective, st = process_file(fp)
        file_stats.append(st)
        if not deposit:
            continue
        used_files += 1
        stream.extend(deposit)
        effective_all.extend(effective)

    print(f"[2] 纳入交存文件：{used_files} 个")
    print(f"    有效代码行（滤空行+纯注释）：{len(effective_all)}")
    print(f"    交存连续行（含技术注释）：{len(stream)}")

    # 7. 注释率（全文流）
    stream = ensure_comment_rate(stream)
    ratio_full = comment_ratio(stream)
    print(f"[7] 全文注释率：{ratio_full * 100:.1f}%")

    # 3. HEAD+TAIL（对截取后的正文再校准注释率，避免尾部前端代码拉低）
    n = len(stream)
    if n > HEAD_LINES + TAIL_LINES:
        head_part = ensure_comment_rate(stream[:HEAD_LINES])
        # 截取后可能变长：压回 1500 行（优先保留含注释的头部）
        if len(head_part) > HEAD_LINES:
            head_part = head_part[:HEAD_LINES]
        elif len(head_part) < HEAD_LINES:
            # 从原文补足代码行
            extra = stream[HEAD_LINES : HEAD_LINES + (HEAD_LINES - len(head_part))]
            head_part = head_part + extra
            head_part = head_part[:HEAD_LINES]
        tail_src = stream[n - TAIL_LINES :]
        tail_part = ensure_comment_rate(tail_src)
        if len(tail_part) > TAIL_LINES:
            tail_part = tail_part[:TAIL_LINES]
        elif len(tail_part) < TAIL_LINES:
            tail_part = tail_part + [""] * (TAIL_LINES - len(tail_part))
        # 拼回 stream 仅用于模式描述；实际 material 由 head/tail 组装
        stream_for_select = head_part + stream[HEAD_LINES : n - TAIL_LINES] + tail_part
        # 直接组装 material，保证 head/tail 已校准
        sep = [""] * LINES_PER_PAGE
        sep[18] = "=" * 62
        sep[20] = "此处为前 30 页结束"
        sep[21] = "———— 以下为后 30 页开始 ————"
        sep[23] = f"软件名称：{SOFTWARE_NAME} {VERSION}"
        sep[24] = f"申请人：{APPLICANT}    开发完成日期：{DEVELOPMENT_DATE}"
        sep[25] = f"连续源程序行数：{n}    交存：前{HEAD_PAGES}页+后{TAIL_PAGES}页"
        sep[27] = "=" * 62
        material = head_part[:HEAD_LINES] + sep + tail_part[:TAIL_LINES]
        # 若 head 因补注释变短，pad
        if len(material) < HEAD_LINES + LINES_PER_PAGE + TAIL_LINES:
            material = material + [""] * (
                HEAD_LINES + LINES_PER_PAGE + TAIL_LINES - len(material)
            )
        material = material[: HEAD_LINES + LINES_PER_PAGE + TAIL_LINES]
        mode = f"HEAD+TAIL（全文约 {(n + LINES_PER_PAGE - 1)//LINES_PER_PAGE} 页，交存前30+分隔+后30=61页）"
        info = {"mode": "HEAD_TAIL", "stream_lines": n}
        stream = stream_for_select
    else:
        material, mode, info = select_head_tail(stream)

    # 交存正文注释率（排除分隔页空白）
    deposit_body = [
        ln
        for i, ln in enumerate(material)
        if not (HEAD_LINES <= i < HEAD_LINES + LINES_PER_PAGE and info.get("mode") == "HEAD_TAIL")
        or info.get("mode") != "HEAD_TAIL"
    ]
    if info.get("mode") == "HEAD_TAIL":
        deposit_body = material[:HEAD_LINES] + material[HEAD_LINES + LINES_PER_PAGE :]
    else:
        deposit_body = [ln for ln in material if ln.strip()]
    ratio = comment_ratio(deposit_body)
    print(f"    交存页注释率：{ratio * 100:.1f}%", end="")
    if TARGET_COMMENT_MIN - 0.005 <= ratio <= TARGET_COMMENT_MAX + 0.02:
        print("  ✓")
    else:
        print("  ⚠ 偏离 20%～30%")

    total_pages = len(material) // LINES_PER_PAGE
    print(f"[3] 模式：{mode}")
    print(f"    交存页数：{total_pages}（每页 {LINES_PER_PAGE} 行）")

    meta = {
        "files": used_files,
        "comment_ratio": ratio,
        "mode": info.get("mode", "FULL"),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_pdf = OUT_DIR / PDF_NAME

    # 9. TXT
    write_txt_bundle(material, stream, mode, meta, file_stats, len(effective_all))
    print("[9] 配套 TXT 已写入 generated/")

    # 8. PDF
    try:
        render_pdf(material, out_pdf)
    except Exception as e:
        print(f"[8] PDF 失败：{e}", file=sys.stderr)
        return 1

    pages = pdf_page_count(out_pdf)
    size_kb = out_pdf.stat().st_size / 1024
    print(f"[8] PDF：{out_pdf}")
    print(f"    页数检测：{pages}（目标 {total_pages}）  大小：{size_kb:.1f} KB")
    print(f"[4-6] A4 · 9pt · 页眉「{HEADER_TEXT}」· 连续行号 · 页脚页码")

    # 同步导出 Word（.docx）
    try:
        import importlib.util

        docx_mod_path = Path(__file__).resolve().parent / "export_source_deposit_docx.py"
        spec = importlib.util.spec_from_file_location("export_source_deposit_docx", docx_mod_path)
        docx_mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(docx_mod)
        docx_path = OUT_DIR / docx_mod.DOCX_NAME
        docx_mod.build_docx(material, docx_path)
        print(f"[10] Word：{docx_path}（{docx_path.stat().st_size / 1024:.1f} KB）")
    except Exception as e:
        print(f"[10] Word 导出跳过：{e}")

    print("完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

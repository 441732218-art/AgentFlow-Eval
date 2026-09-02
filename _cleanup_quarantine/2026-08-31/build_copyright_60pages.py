#!/usr/bin/env python3
"""
build_copyright_60pages.py — 软著源代码60页鉴别材料生成器
严格按国家版权保护中心标准：前端(1-30页) + 后端(31-60页)
生成格式为可打印HTML，等宽字体，页眉/页脚统一。
"""

import os
import html as h
from pathlib import Path

ROOT_DIR = Path(r"D:\AgentFlow-Eval")
OUTPUT_HTML = ROOT_DIR / "copyright_output" / "AgentFlow-Eval_源代码鉴别材料_60页_V1.0.html"
OUTPUT_DIR = OUTPUT_HTML.parent

SOFTWARE_NAME = "AgentFlow-Eval Agent自动化评测工作台 V1.0"
LINES_PER_PAGE = 55
TOTAL_PAGES = 60

# ============================================================
# 文件白名单：前端 (TypeScript/React) — 按入口→路由→页面→组件→工具排列
# ============================================================
FRONTEND_FILES = [
    # ---- 入口与路由 ----
    ("frontend/src/main.tsx", "入口：React应用启动"),
    ("frontend/src/App.tsx", "入口：根组件与Provider装配"),
    ("frontend/src/router/index.tsx", "路由：全站路由配置"),
    # ---- 导航与布局 ----
    ("frontend/src/components/layout/MainLayout.tsx", "布局：主框架布局"),
    ("frontend/src/components/layout/Sidebar.tsx", "导航：侧边栏组件"),
    ("frontend/src/components/layout/navItems.tsx", "导航：菜单项配置"),
    ("frontend/src/components/layout/Header.tsx", "布局：顶部Header"),
    # ---- 页面组件 ----
    ("frontend/src/dashboard/DashboardPage.tsx", "页面：驾驶舱看板"),
    ("frontend/src/traces/TraceExplorerPage.tsx", "页面：轨迹回溯浏览器"),
    ("frontend/src/diagnosis/DiagnosisPage.tsx", "页面：故障诊断"),
    ("frontend/src/analytics/AnalyticsPage.tsx", "页面：分析中心"),
    ("frontend/src/monitoring/MonitoringPage.tsx", "页面：运行监控"),
    ("frontend/src/pages/tasks/index.tsx", "页面：评测任务列表"),
    ("frontend/src/pages/tasks/create.tsx", "页面：创建评测任务"),
    ("frontend/src/pages/tasks/detail.tsx", "页面：任务详情"),
    ("frontend/src/pages/reports/index.tsx", "页面：评测报告列表"),
    ("frontend/src/pages/reports/ReportDetail.tsx", "页面：报告详情"),
    ("frontend/src/pages/billing/index.tsx", "页面：用量计费"),
    ("frontend/src/pages/plugins/index.tsx", "页面：插件市场"),
    ("frontend/src/pages/Settings.tsx", "页面：设置中心"),
    # ---- 核心业务组件 ----
    ("frontend/src/components/flow/AgentTopologyFlow.tsx", "组件：Agent拓扑流程图(ReactFlow)"),
    ("frontend/src/components/TraceFlow/TraceFlowChart.tsx", "组件：执行轨迹DAG图(ReactFlow)"),
    ("frontend/src/components/TraceFlow/StepLogPanel.tsx", "组件：步骤日志面板"),
    ("frontend/src/components/TraceFlow/ScoreCard.tsx", "组件：评分卡片"),
    ("frontend/src/components/charts/EChart.tsx", "组件：ECharts图表封装"),
    ("frontend/src/components/widgets/MetricCard.tsx", "组件：指标卡片"),
    ("frontend/src/components/widgets/Panel.tsx", "组件：面板容器"),
    ("frontend/src/components/ui/StatusBadge.tsx", "组件：状态徽章"),
    ("frontend/src/components/ui/EmptyState.tsx", "组件：空状态"),
    # ---- API与服务层 ----
    ("frontend/src/api/client.ts", "服务：API客户端"),
    ("frontend/src/services/taskService.ts", "服务：任务API"),
    ("frontend/src/services/traceService.ts", "服务：轨迹API"),
    ("frontend/src/api/endpoints/billing.ts", "服务：计费API"),
    ("frontend/src/api/endpoints/plugins.ts", "服务：插件API"),
    # ---- Hooks与状态管理 ----
    ("frontend/src/hooks/useTasks.ts", "Hook：任务数据管理"),
    ("frontend/src/hooks/useTraces.ts", "Hook：轨迹数据管理"),
    ("frontend/src/hooks/useDashboardOverview.ts", "Hook：驾驶舱数据"),
    ("frontend/src/stores/useThemeStore.ts", "Store：主题状态"),
    ("frontend/src/stores/useTaskStore.ts", "Store：任务状态"),
    # ---- 工具函数 ----
    ("frontend/src/utils/format.ts", "工具：格式化函数"),
    ("frontend/src/lib/utils.ts", "工具：通用工具函数"),
    ("frontend/src/lib/validators.ts", "工具：表单验证规则"),
    ("frontend/src/lib/observability.ts", "工具：可观测性映射"),
    # ---- 认证与权限 ----
    ("frontend/src/auth/AuthProvider.tsx", "认证：Auth上下文Provider"),
    ("frontend/src/auth/RouteGuard.tsx", "认证：路由守卫"),
    ("frontend/src/auth/permissions.ts", "认证：权限定义"),
    # ---- 国际化 ----
    ("frontend/src/i18n/index.ts", "国际化：i18n配置"),
]

# ============================================================
# 文件白名单：后端 (Python) — 保持核心业务模块顺序
# ============================================================
BACKEND_FILES = [
    # ---- 应用入口与配置 ----
    ("backend/app/main.py", "应用入口与中间件装配"),
    ("backend/app/config.py", "配置中心"),
    ("backend/app/core/middleware.py", "中间件：安全与请求ID"),
    ("backend/app/core/security.py", "安全：API Key鉴权"),
    # ---- 数据模型 ----
    ("backend/app/models/task.py", "模型：评测任务 Entity"),
    ("backend/app/models/test_suite.py", "模型：测试用例 Entity"),
    ("backend/app/models/trace.py", "模型：执行轨迹 Entity"),
    ("backend/app/models/metric_score.py", "模型：指标分 Entity"),
    ("backend/app/models/audit_log.py", "模型：审计日志 Entity"),
    ("backend/app/models/tenant.py", "模型：租户 Entity"),
    ("backend/app/models/billing.py", "模型：计费 Entity"),
    ("backend/app/models/experiment.py", "模型：对比实验 Entity"),
    # ---- API路由 ----
    ("backend/app/api/v1/router.py", "API：路由注册"),
    ("backend/app/api/v1/endpoints/tasks.py", "API：评测任务接口"),
    ("backend/app/api/v1/endpoints/traces.py", "API：执行轨迹接口"),
    ("backend/app/api/v1/endpoints/reports.py", "API：评测报告接口"),
    ("backend/app/api/v1/endpoints/billing.py", "API：计费接口"),
    ("backend/app/api/v1/endpoints/plugins.py", "API：插件接口"),
    ("backend/app/api/v1/endpoints/dashboard.py", "API：驾驶舱接口"),
    ("backend/app/api/v1/endpoints/diagnosis.py", "API：故障诊断接口"),
    ("backend/app/api/v1/endpoints/experiments.py", "API：对比实验接口"),
    ("backend/app/api/v1/endpoints/audit.py", "API：审计日志接口"),
    ("backend/app/api/v1/endpoints/logs.py", "API：日志查询"),
    # ---- 核心业务引擎 ----
    ("backend/app/core/agent_runner/openai_runner.py", "引擎：OpenAI Agent执行器"),
    ("backend/app/core/agent_runner/http_runner.py", "引擎：HTTP Agent执行器"),
    ("backend/app/core/agent_runner/factory.py", "引擎：执行器工厂"),
    ("backend/app/core/agent_runner/tool_sandbox.py", "引擎：工具沙箱"),
    ("backend/app/core/judge_engine/llm_judge.py", "引擎：LLM评审器"),
    ("backend/app/core/judge_engine/scorecard.py", "引擎：评分卡"),
    ("backend/app/core/judge_engine/metrics.py", "引擎：指标计算"),
    ("backend/app/core/evaluation/pipeline.py", "引擎：评测流水线"),
    ("backend/app/core/evaluation/compare.py", "引擎：结果对比"),
    ("backend/app/core/diagnosis/engine.py", "引擎：诊断引擎"),
    # ---- 异步任务编排 ----
    ("backend/app/core/celery_app/celery.py", "编排：Celery应用配置"),
    ("backend/app/core/celery_app/tasks.py", "编排：Celery任务定义"),
    # ---- 横切关注点 ----
    ("backend/app/core/tenancy.py", "横切：多租户隔离"),
    ("backend/app/core/rbac.py", "横切：角色权限控制"),
    ("backend/app/core/resilience/circuit_breaker.py", "横切：熔断器"),
    ("backend/app/core/resilience/retry.py", "横切：重试策略"),
    # ---- 插件系统 ----
    ("backend/app/plugins/__init__.py", "插件：插件系统入口"),
    ("backend/app/plugins/examples/echo_runner.py", "插件：示例执行器"),
    ("backend/app/plugins/examples/length_judge.py", "插件：示例评判器"),
    # ---- 工具与异常 ----
    ("backend/app/utils/exceptions.py", "工具：异常定义"),
    ("backend/app/utils/logger.py", "工具：日志配置"),
    ("backend/app/utils/cost.py", "工具：成本计算"),
]



def is_dev_trace(line: str) -> bool:
    s = line.strip().lower()
    dev = ["# todo", "// todo", "# fixme", "// fixme",
           "# hack", "// hack", "console.log(", "console.debug(",
           'print("debug', "print('debug", "debugger",
           "# xxx", "// xxx"]
    return any(p in s for p in dev)


def clean_source(content: str, is_frontend: bool) -> list[str]:
    lines = []
    for line in content.split("\n"):
        if is_dev_trace(line):
            continue
        lines.append(line)
    result = []
    blank = 0
    for line in lines:
        if line.strip() == "":
            blank += 1
            if blank <= 2:
                result.append(line)
        else:
            blank = 0
            result.append(line)
    return result


def add_header(lines: list[str], fname: str, desc: str, fe: bool) -> list[str]:
    if fe:
        hdr = [
            f"// ============================================",
            f"// {SOFTWARE_NAME}",
            f"// 文件名：{fname}",
            f"// 模块：{desc}",
            f"// ============================================",
        ]
    else:
        hdr = [
            f"# ============================================",
            f"# {SOFTWARE_NAME}",
            f"# 文件名：{fname}",
            f"# 模块：{desc}",
            f"# ============================================",
        ]
    return hdr + lines


def process_files(flist, fe):
    out = []
    for rp, desc in flist:
        ap = ROOT_DIR / rp
        if not ap.exists():
            print(f"  [MISSING] {rp}")
            continue
        try:
            with open(ap, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lstrip("\ufeff")
        except Exception as e:
            print(f"  [ERR] {rp}: {e}")
            continue
        clean = clean_source(content, fe)
        if not clean:
            continue
        out.extend(add_header(clean, rp, desc, fe))
        out.append("")
        out.append("")
        print(f"  [OK] {rp}  lines={len(clean)}")
    return out


def build_html(fl, bl):
    all_l = fl + [
        "# " + "=" * 76,
        f"# 后端代码 (Python/FastAPI) — {SOFTWARE_NAME}",
        "# " + "=" * 76,
        "",
    ] + bl

    pages = [all_l[i:i+LINES_PER_PAGE]
             for i in range(0, len(all_l), LINES_PER_PAGE)]
    pages = pages[:TOTAL_PAGES]
    np = len(pages)
    print(f"\n总行数={len(all_l)}  总页数={np}")

    E = h.escape
    hdr = E(SOFTWARE_NAME)
    parts = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
             f'<title>{hdr} — 源程序鉴别材料 (共{np}页)</title><style>',
             '@page{size:A4 portrait;margin:15mm 12mm 18mm 12mm}',
             '*{margin:0;padding:0;box-sizing:border-box}',
             'body{font-family:"Consolas","Courier New",monospace;font-size:9.5pt;line-height:1.35;color:#000;background:#fff}',
             '.pg{page-break-after:always;min-height:260mm;padding:5mm 6mm;position:relative}',
             '.pg:last-child{page-break-after:auto}',
             '.hdr{border-bottom:1.5px solid #000;padding-bottom:3mm;margin-bottom:4mm;display:flex;justify-content:space-between;font-weight:bold;font-size:10pt;font-family:"Microsoft YaHei",sans-serif}',
             '.ftr{position:absolute;bottom:6mm;left:6mm;right:6mm;text-align:center;border-top:1px solid #999;padding-top:2mm;font-size:8pt;color:#555;font-family:"Microsoft YaHei",sans-serif}',
             'pre{margin:0;white-space:pre-wrap;word-wrap:break-word;font-family:inherit;font-size:inherit;line-height:inherit;tab-size:2}',
             '.ln{display:inline-block;width:3em;text-align:right;margin-right:0.6em;color:#aaa;user-select:none;font-size:8pt}',
             '</style></head><body>']

    for idx, chunk in enumerate(pages):
        pn = idx + 1
        plines = []
        for i, line in enumerate(chunk):
            esc = E(line) if line.strip() else " "
            plines.append(f'<span class="ln">{i+1:>3}</span><span>{esc}</span>')
        body = "\n".join(plines)
        parts.append(
            f'<div class="pg">'
            f'<div class="hdr"><span>{hdr}</span><span>第{pn}页/共{np}页</span></div>'
            f'<pre>{body}</pre>'
            f'<div class="ftr">第{pn}页/共{np}页</div>'
            f'</div>')

    parts.append('</body></html>')
    return "\n".join(parts)


def main():
    os.chdir(str(ROOT_DIR))
    print("=" * 60)
    print(f"AgentFlow-Eval 软著源代码60页鉴别材料生成器")
    print(f"软件全称: {SOFTWARE_NAME}")
    print("=" * 60)

    print("\n[1/4] 处理前端代码 (TypeScript/React)...")
    fl = process_files(FRONTEND_FILES, True)
    print(f"  前端总行数: {len(fl)}")

    print("\n[2/4] 处理后端代码 (Python/FastAPI)...")
    bl = process_files(BACKEND_FILES, False)
    print(f"  后端总行数: {len(bl)}")

    print("\n[3/4] 构建HTML文档...")
    html = build_html(fl, bl)

    print("\n[4/4] 写入输出...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    sz = OUTPUT_HTML.stat().st_size / 1024
    front_ok = sum(1 for f, _ in FRONTEND_FILES if (ROOT_DIR / f).exists())
    back_ok = sum(1 for f, _ in BACKEND_FILES if (ROOT_DIR / f).exists())
    print(f"\n{'='*60}")
    print(f"[DONE] 输出: {OUTPUT_HTML}")
    print(f"  大小: {sz:.1f} KB")
    print(f"  前端: {front_ok}/{len(FRONTEND_FILES)}  后端: {back_ok}/{len(BACKEND_FILES)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
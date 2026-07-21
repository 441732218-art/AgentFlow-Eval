# (c) 2026 AgentFlow-Eval
"""路由注册总入口 —— 聚合所有 v1 版本的路由并注册到主路由器。"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ab,
    agents_http,
    audit,
    benchmarks,
    billing,
    dashboard,
    diagnosis,
    experiments,
    judges,
    logs,
    me,
    media,
    observability,
    plugins,
    reports,
    settings,
    tasks,
    tenants,
    tools,
    traces,
    ws,
)

router = APIRouter(prefix="/api/v1")

router.include_router(me.router, prefix="/me", tags=["当前用户"])
router.include_router(tenants.router, prefix="/tenants", tags=["多租户"])
router.include_router(billing.router, prefix="/billing", tags=["计费"])
router.include_router(benchmarks.router, prefix="/benchmarks", tags=["Benchmark"])
router.include_router(observability.router, prefix="/observability", tags=["可观测"])
router.include_router(tasks.router, prefix="/tasks", tags=["评测任务"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["仪表板"])
router.include_router(diagnosis.router, prefix="/diagnosis", tags=["故障诊断"])
router.include_router(logs.router, prefix="/logs", tags=["可观测日志"])
router.include_router(media.router, prefix="/media", tags=["多模态"])
router.include_router(ab.router, prefix="/ab", tags=["A/B测试"])
router.include_router(experiments.router, prefix="/experiments", tags=["对比实验"])
router.include_router(traces.router, prefix="/traces", tags=["执行轨迹"])
router.include_router(reports.router, prefix="/reports", tags=["评测报告"])
router.include_router(audit.router, prefix="/audit", tags=["审计日志"])
router.include_router(tools.router, prefix="/tools", tags=["工具沙箱"])
router.include_router(agents_http.router, prefix="/agents/http", tags=["HTTP Agent"])
router.include_router(judges.router, prefix="/judges", tags=["Judge 评分卡"])
router.include_router(plugins.router, prefix="/plugins", tags=["插件系统"])
router.include_router(settings.router, prefix="/settings", tags=["系统设置"])
router.include_router(ws.router, tags=["实时推送"])

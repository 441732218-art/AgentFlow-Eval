# (c) 2026 AgentFlow-Eval
"""路由注册总入口 —— 聚合所有 v1 版本的路由并注册到主路由器。"""

from fastapi import APIRouter

from app.api.v1.endpoints import audit, reports, settings, tasks, tools, traces, ws

router = APIRouter(prefix="/api/v1")

router.include_router(tasks.router, prefix="/tasks", tags=["评测任务"])
router.include_router(traces.router, prefix="/traces", tags=["执行轨迹"])
router.include_router(reports.router, prefix="/reports", tags=["评测报告"])
router.include_router(audit.router, prefix="/audit", tags=["审计日志"])
router.include_router(tools.router, prefix="/tools", tags=["工具沙箱"])
router.include_router(settings.router, prefix="/settings", tags=["系统设置"])
router.include_router(ws.router, tags=["实时推送"])

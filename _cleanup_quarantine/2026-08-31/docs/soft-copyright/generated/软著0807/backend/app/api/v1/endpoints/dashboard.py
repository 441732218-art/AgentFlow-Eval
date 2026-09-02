# (c) 2026 AgentFlow-Eval | Author: 李凯昕
# AgentFlow-Eval Agent自动化评测工作台 V1.0
"""Dashboard stats API with short-TTL cache + Intelligence Center overview."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db
from app.core.rbac import Permission, get_request_role, require_permission
router = APIRouter()
@router.get("/stats")
@require_permission(Permission.TASK_READ)
async def dashboard_stats(
request: Request,
session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
"""Return aggregated task counts for the current actor (cached 1 min)."""
from app.core.cache.services import get_cached_dashboard
actor = getattr(request.state, "actor", None) or "anonymous"
role = get_request_role(request).value
return await get_cached_dashboard(session, actor=actor, role=role)
def _build_topology(
*,
running: int,
completed: int,
failed: int,
avg_score: float | None,
latency_ms: float | None,
tokens: int,
success_rate: float | None,
model_hint: str | None = None,
) -> dict[str, Any]:
"""Horizontal ReAct pipeline topology for ReactFlow cockpit."""
tool_status = (
"error" if failed > max(completed, 1) else ("warn" if failed else "ok")
)
planner_status = "ok" if running or completed else "idle"
if running:
planner_status = "ok"
judge_status = "ok" if completed else ("warn" if failed else "idle")
observe_status = "warn" if failed else "ok"
lat_label = f"{round(latency_ms)} ms" if latency_ms is not None else "—"
score_label = f"{avg_score:.1f}" if avg_score is not None else "—"
sr = f"{success_rate * 100:.1f}%" if success_rate is not None else "—"
nodes = [
{
"id": "user",
"label": "User Request",
"status": "ok",
"kind": "ingress",
"meta": {
"type": "ingress",
"input": "Business query / test suite",
"output": "→ Planner",
"latency": "< 1 ms",
"model": "—",
},
},
{
"id": "planner",
"label": "Planner Agent",
"status": planner_status,
"kind": "agent",
"meta": {
"type": "agent",
"running": running,
"input": "User query + system prompt",
"output": "Thought / plan / tool plan",
"token": tokens // max(running + completed, 1) if tokens else 0,
"latency": lat_label,
"model": model_hint or "openai-compatible",
},
},
{
"id": "tool",
"label": "Tool Calling",
"status": tool_status,
"kind": "tool",
"meta": {
"type": "tool",
"failed": failed,
"input": "Function call args",
"output": "Tool observation payload",
"latency": "sandbox",
"error": f"{failed} failed tasks" if failed else "",
},
},
{
"id": "observe",
"label": "Observation",
"status": observe_status,
"kind": "observe",
"meta": {
"type": "observe",
"input": "Tool result",
"output": "Normalized observation",
"latency": lat_label,
},
},
{
"id": "judge",
"label": "LLM Judge",
"status": judge_status,
"kind": "judge",
"meta": {
"type": "judge",
"score": avg_score,
"input": "Trace + expected",
"output": f"Score {score_label} · SR {sr}",
"latency": lat_label,
"model": "judge-engine",
},
},
]
edges = [
{"source": "user", "target": "planner", "label": "dispatch"},
{"source": "planner", "target": "tool", "label": "act"},
{"source": "tool", "target": "observe", "label": "result"},
{"source": "observe", "target": "judge", "label": "score"},
]
if failed:
edges.append(
{
"source": "observe",
"target": "planner",
"type": "loop",
"label": "retry",
}
)
return {
"layout": "horizontal",
"nodes": nodes,
"edges": edges,
"legend": [
{"status": "ok", "label": "Healthy"},
{"status": "warn", "label": "Degraded"},
{"status": "error", "label": "Failure"},
{"status": "idle", "label": "Idle"},
],
}
@router.get("")
@router.get("/overview")
@require_permission(Permission.TASK_READ)
async def dashboard_overview(
request: Request,
days: int = Query(7, ge=1, le=90),
session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
"""Intelligence Center cockpit payload for ECharts + ReactFlow."""
from app.core.cache.services import get_cached_dashboard
from app.core.observability.business_kpis import compute_kpis
from app.core.observability.timeseries import compute_dashboard_series
actor = getattr(request.state, "actor", None) or "anonymous"
role = get_request_role(request).value
# === SEGMENT_BREAK ===
—— 第 30 页之后省略中间部分源代码 ——
（前30页完，以下为后30页）
class ExperimentRun(PKMixin, TenantMixin, TimestampMixin, Base):
"""One evaluation run inside an experiment (maps 1:1 to a Task)."""
__tablename__ = "experiment_runs"
__table_args__ = (
UniqueConstraint("experiment_id", "label", name="uq_experiment_run_label"),
Index("ix_experiment_runs_tenant", "tenant_id"),
)
experiment_id: Mapped[str] = mapped_column(
String(36),
ForeignKey("experiments.id", ondelete="CASCADE"),
nullable=False,
index=True,
comment="所属实验",
)
task_id: Mapped[str] = mapped_column(
String(36),
ForeignKey("tasks.id", ondelete="CASCADE"),
nullable=False,
index=True,
comment="对应评测任务",
)
label: Mapped[str] = mapped_column(
String(100),
nullable=False,
comment="变体标签，如 gpt-4o / http-agent-v1",
)
agent_config: Mapped[dict[str, Any]] = mapped_column(
JSON,
nullable=False,
default=dict,
comment="该 run 使用的 agent_config 快照",
)
experiment: Mapped[Experiment] = relationship(back_populates="runs")
task: Mapped[Task] = relationship()
def __repr__(self) -> str:
return f"<ExperimentRun id={self.id} label={self.label!r} task={self.task_id}>"

# (c) 2026 AgentFlow-Eval
"""Benchmark service — create, import cases, run via Evaluation Engine, leaderboard."""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.benchmark import (
    Benchmark,
    BenchmarkCase,
    BenchmarkResult,
    BenchmarkRun,
)
from app.models.metric_score import MetricScore
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.models.trace import Trace
from app.utils.exceptions import AgentFlowError, NotFoundError

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BenchmarkService:
    async def create_benchmark(
        self,
        session: AsyncSession,
        *,
        name: str,
        description: str = "",
        created_by: str = "anonymous",
        tenant_id: str | None = None,
        tags: list[str] | None = None,
        cases: list[dict[str, Any]] | None = None,
        version: str = "1.0",
        scorecard: dict[str, Any] | None = None,
        source_task_id: str | None = None,
    ) -> Benchmark:
        meta: dict[str, Any] = {
            "version": (version or "1.0").strip()[:64],
        }
        if scorecard and isinstance(scorecard, dict):
            meta["scorecard"] = scorecard
        if source_task_id:
            meta["source_task_id"] = source_task_id
        bm = Benchmark(
            id=str(uuid4()),
            name=name.strip(),
            description=description or "",
            status="active",
            created_by=created_by,
            tenant_id=tenant_id,
            tags=list(tags or []),
            meta=meta,
        )
        session.add(bm)
        await session.flush()
        if cases:
            await self.add_cases(
                session,
                bm,
                cases,
                tenant_id=tenant_id,
            )
        return bm

    async def create_from_task(
        self,
        session: AsyncSession,
        *,
        task_id: str,
        name: str | None = None,
        description: str = "",
        version: str = "1.0",
        created_by: str = "anonymous",
        tenant_id: str | None = None,
        scorecard: dict[str, Any] | None = None,
    ) -> Benchmark:
        """Build a Benchmark from an existing Task's test suites + optional scorecard."""
        task = (
            await session.execute(select(Task).where(Task.id == task_id))
        ).scalar_one_or_none()
        if task is None:
            raise NotFoundError("Task", task_id)
        suites = (
            (
                await session.execute(
                    select(TestSuite).where(TestSuite.task_id == task_id)
                )
            )
            .scalars()
            .all()
        )
        if not suites:
            raise AgentFlowError(
                "Task has no test suites — add cases first", status_code=400
            )
        cases = [
            {
                "name": f"suite-{i + 1}",
                "user_query": s.user_query,
                "expected_output": s.expected_output or "",
                "expected_tools": list(s.expected_tools or []),
            }
            for i, s in enumerate(suites)
        ]
        ac = dict(task.agent_config or {})
        sc = scorecard
        if sc is None and isinstance(ac.get("scorecard"), dict):
            sc = ac["scorecard"]
        return await self.create_benchmark(
            session,
            name=(name or f"Bench · {task.name}")[:255],
            description=description
            or f"From task {task_id}: {task.description or ''}"[:2000],
            created_by=created_by,
            tenant_id=tenant_id or getattr(task, "tenant_id", None),
            cases=cases,
            version=version,
            scorecard=sc,
            source_task_id=task_id,
        )

    async def add_cases(
        self,
        session: AsyncSession,
        benchmark: Benchmark,
        cases: list[dict[str, Any]],
        *,
        tenant_id: str | None = None,
    ) -> list[BenchmarkCase]:
        created: list[BenchmarkCase] = []
        for i, raw in enumerate(cases):
            if not isinstance(raw, dict):
                continue
            query = (
                raw.get("user_query")
                or raw.get("query")
                or raw.get("input")
                or raw.get("prompt")
                or ""
            ).strip()
            if not query:
                continue
            case = BenchmarkCase(
                id=str(uuid4()),
                benchmark_id=benchmark.id,
                name=(raw.get("name") or raw.get("id") or f"case-{i + 1}")[:255],
                user_query=query,
                expected_output=str(
                    raw.get("expected_output")
                    or raw.get("expected")
                    or raw.get("output")
                    or ""
                ),
                expected_tools=list(
                    raw.get("expected_tools") or raw.get("tools") or []
                ),
                weight=float(raw.get("weight") or 1.0),
                extra_metadata=dict(raw.get("extra_metadata") or raw.get("meta") or {}),
                tenant_id=tenant_id or benchmark.tenant_id,
            )
            session.add(case)
            created.append(case)
        await session.flush()
        return created

    def parse_import_payload(self, *, content: str, fmt: str) -> list[dict[str, Any]]:
        fmt = (fmt or "json").lower().strip()
        if fmt == "json":
            data = json.loads(content)
            if isinstance(data, dict):
                data = data.get("cases") or data.get("items") or data.get("data") or []
            if not isinstance(data, list):
                raise AgentFlowError("JSON must be a list of cases", status_code=422)
            return [c for c in data if isinstance(c, dict)]
        if fmt == "csv":
            reader = csv.DictReader(io.StringIO(content))
            rows: list[dict[str, Any]] = []
            for row in reader:
                tools = row.get("expected_tools") or ""
                tool_list = (
                    [t.strip() for t in tools.split("|") if t.strip()] if tools else []
                )
                rows.append(
                    {
                        "name": row.get("name") or row.get("id") or "",
                        "user_query": row.get("user_query")
                        or row.get("query")
                        or row.get("input")
                        or "",
                        "expected_output": row.get("expected_output")
                        or row.get("expected")
                        or "",
                        "expected_tools": tool_list,
                        "weight": float(row.get("weight") or 1.0),
                    }
                )
            return rows
        raise AgentFlowError(f"Unsupported format: {fmt}", status_code=422)

    async def get_benchmark(
        self, session: AsyncSession, benchmark_id: str, *, with_cases: bool = True
    ) -> Benchmark:
        opts = []
        if with_cases:
            opts.append(selectinload(Benchmark.cases))
        r = await session.execute(
            select(Benchmark)
            .options(*opts)
            .where(Benchmark.id == benchmark_id)
            .execution_options(populate_existing=True)
        )
        bm = r.scalar_one_or_none()
        if bm is None:
            raise NotFoundError("Benchmark", benchmark_id)
        return bm

    async def list_benchmarks(
        self,
        session: AsyncSession,
        *,
        actor: str | None = None,
        tenant_id: str | None = None,
        limit: int = 50,
    ) -> list[Benchmark]:
        q = select(Benchmark).where(Benchmark.status != "deleted")
        if tenant_id:
            q = q.where(Benchmark.tenant_id == tenant_id)
        q = q.order_by(Benchmark.created_at.desc()).limit(min(limit, 200))
        rows = await session.execute(q)
        return list(rows.scalars().all())

    async def run_benchmark(
        self,
        session: AsyncSession,
        *,
        benchmark_id: str,
        actor: str,
        agent_config: dict[str, Any] | None = None,
        label: str = "default",
        tenant_id: str | None = None,
        enqueue: bool = True,
    ) -> BenchmarkRun:
        """Create Task + suites from cases and enqueue Evaluation Engine."""
        bm = await self.get_benchmark(session, benchmark_id, with_cases=True)
        if not bm.cases:
            raise AgentFlowError(
                "Benchmark has no cases — import JSON/CSV first",
                status_code=400,
            )

        cfg = dict(agent_config or {"model": "gpt-4o-mini", "temperature": 0})
        # Bind benchmark scorecard into agent_config for Judge (Phase 3/4)
        meta = dict(bm.meta or {})
        if isinstance(meta.get("scorecard"), dict) and "scorecard" not in cfg:
            cfg["scorecard"] = meta["scorecard"]
        if "runner" not in cfg and "endpoint_url" not in cfg:
            cfg.setdefault("runner", "openai")

        task = Task(
            id=str(uuid4()),
            name=f"[benchmark] {bm.name} / {label}"[:255],
            description=f"Benchmark run for {bm.id} v{meta.get('version', '1.0')}",
            agent_config=cfg,
            status=TaskStatus.CREATED,
            created_by=actor,
            tenant_id=tenant_id or bm.tenant_id,
        )
        session.add(task)
        await session.flush()

        for case in bm.cases:
            session.add(
                TestSuite(
                    id=str(uuid4()),
                    task_id=task.id,
                    user_query=case.user_query,
                    expected_output=case.expected_output or "",
                    expected_tools=list(case.expected_tools or []),
                    extra_metadata={
                        "benchmark_id": bm.id,
                        "benchmark_case_id": case.id,
                        "weight": case.weight,
                    },
                    tenant_id=tenant_id or bm.tenant_id,
                )
            )
        await session.flush()

        run = BenchmarkRun(
            id=str(uuid4()),
            benchmark_id=bm.id,
            task_id=task.id,
            label=(label or "default")[:128],
            agent_config=cfg,
            status="queued" if enqueue else "pending",
            created_by=actor,
            tenant_id=tenant_id or bm.tenant_id,
            started_at=_now(),
            summary={
                "case_count": len(bm.cases),
                "benchmark_version": meta.get("version") or "1.0",
            },
        )
        session.add(run)
        await session.flush()

        if enqueue:
            try:
                from app.core.profiles import get_task_queue

                task.status = TaskStatus.QUEUED
                queue = get_task_queue()
                enq = queue.enqueue("run_full_evaluation", args=(task.id,))
                task.celery_task_id = enq.task_id
                run.status = "running"
            except Exception as exc:
                logger.warning("Benchmark enqueue failed: %s", exc)
                run.status = "pending"
                run.summary = {
                    **(run.summary or {}),
                    "enqueue_error": str(exc),
                }

        # Meter as one task usage (best-effort)
        try:
            from app.core.billing.service import get_billing_service

            await get_billing_service().ensure_task_quota(session, actor)
            await get_billing_service().record_usage(
                session,
                actor=actor,
                metric="task",
                quantity=1,
                ref_type="benchmark_run",
                ref_id=run.id,
            )
        except Exception:
            pass

        await session.flush()
        return run

    async def finalize_run(self, session: AsyncSession, run_id: str) -> BenchmarkRun:
        """Materialize BenchmarkResult rows from Task traces + metric_scores."""
        r = await session.execute(
            select(BenchmarkRun)
            .options(selectinload(BenchmarkRun.results))
            .where(BenchmarkRun.id == run_id)
        )
        run = r.scalar_one_or_none()
        if run is None:
            raise NotFoundError("BenchmarkRun", run_id)
        if not run.task_id:
            raise AgentFlowError("Run has no linked task", status_code=400)

        # Clear previous results (re-finalize)
        for old in list(run.results or []):
            await session.delete(old)
        await session.flush()

        suites = (
            (
                await session.execute(
                    select(TestSuite).where(TestSuite.task_id == run.task_id)
                )
            )
            .scalars()
            .all()
        )

        total_tokens = 0
        total_cost = 0.0
        latencies: list[float] = []
        accuracies: list[float] = []
        qualities: list[float] = []
        scores: list[float] = []
        dim_buckets: dict[str, list[float]] = {}
        success_count = 0
        scored_count = 0

        for suite in suites:
            traces = (
                (
                    await session.execute(
                        select(Trace)
                        .where(Trace.test_suite_id == suite.id)
                        .order_by(Trace.created_at.desc())
                    )
                )
                .scalars()
                .all()
            )
            if not traces:
                continue
            tr = traces[0]
            ms_rows = (
                (
                    await session.execute(
                        select(MetricScore).where(MetricScore.trace_id == tr.id)
                    )
                )
                .scalars()
                .all()
            )
            by_name = {m.metric_name: float(m.score) for m in ms_rows}
            # Prefer scorecard dimensions; fall back to legacy accuracy/quality keys
            accuracy = by_name.get("tool_accuracy") or by_name.get("accuracy")
            quality = by_name.get("answer_correctness") or by_name.get("quality")
            # Total points (scorecard-style sum), not mean of heterogeneous metrics
            overall = sum(by_name.values()) if by_name else None
            rt = getattr(tr, "response_time_ms", None)
            latency = float(rt) if rt is not None else None
            tokens = int(getattr(tr, "total_tokens", None) or 0)
            cost = float(getattr(tr, "cost", None) or 0.0)
            case_id = None
            meta = suite.extra_metadata or {}
            if isinstance(meta, dict):
                case_id = meta.get("benchmark_case_id")

            success = str(getattr(tr, "status", "") or "").lower() in {
                "success",
                "completed",
            }

            br = BenchmarkResult(
                id=str(uuid4()),
                run_id=run.id,
                case_id=case_id,
                trace_id=tr.id,
                accuracy=float(accuracy) if accuracy is not None else overall,
                quality=float(quality) if quality is not None else overall,
                latency_ms=latency,
                cost=cost,
                tokens=tokens,
                score=float(overall) if overall is not None else None,
                detail={
                    "metrics": by_name,
                    "success": success,
                },
                tenant_id=run.tenant_id,
            )
            session.add(br)
            total_tokens += tokens
            total_cost += cost
            if latency is not None:
                latencies.append(latency)
            if br.accuracy is not None:
                accuracies.append(br.accuracy)
            if br.quality is not None:
                qualities.append(br.quality)
            if br.score is not None:
                scores.append(br.score)
            for k, v in by_name.items():
                dim_buckets.setdefault(k, []).append(float(v))
            if success:
                success_count += 1
            if by_name:
                scored_count += 1

        def _avg(xs: list[float]) -> float | None:
            return round(sum(xs) / len(xs), 4) if xs else None

        dim_avgs = {k: _avg(v) for k, v in dim_buckets.items()}
        n_suites = len(suites) or 1
        run.summary = {
            "case_count": len(suites),
            "result_count": len(scores) or len(accuracies),
            "scored_traces": scored_count,
            "success_count": success_count,
            "success_rate": round(success_count / n_suites, 4) if suites else 0.0,
            "score_coverage": round(scored_count / n_suites, 4) if suites else 0.0,
            "accuracy": _avg(accuracies),
            "quality": _avg(qualities),
            "latency_ms": _avg(latencies),
            "cost": round(total_cost, 6),
            "tokens": total_tokens,
            "score": _avg(scores),
            "dimension_scores": dim_avgs,
        }
        task = (
            await session.execute(select(Task).where(Task.id == run.task_id))
        ).scalar_one_or_none()
        if task and task.status == TaskStatus.COMPLETED:
            run.status = "completed"
            run.finished_at = _now()
        elif task and task.status in {
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMEOUT,
        }:
            run.status = "failed"
            run.finished_at = _now()
        elif task and task.status in {
            TaskStatus.RUNNING,
            TaskStatus.QUEUED,
            TaskStatus.JUDGING,
        }:
            run.status = "running"
        await session.flush()
        return run

    async def list_runs(
        self,
        session: AsyncSession,
        benchmark_id: str,
        *,
        limit: int = 50,
    ) -> list[BenchmarkRun]:
        """List evaluation runs for a benchmark (newest first). Auto-finalize pending."""
        await self.get_benchmark(session, benchmark_id, with_cases=False)
        runs = (
            (
                await session.execute(
                    select(BenchmarkRun)
                    .where(BenchmarkRun.benchmark_id == benchmark_id)
                    .order_by(BenchmarkRun.created_at.desc())
                    .limit(min(limit, 200))
                )
            )
            .scalars()
            .all()
        )
        for run in runs:
            if run.status in {"queued", "running", "pending"} and run.task_id:
                try:
                    await self.finalize_run(session, run.id)
                except Exception:
                    pass
        # re-load after finalize
        runs = (
            (
                await session.execute(
                    select(BenchmarkRun)
                    .where(BenchmarkRun.benchmark_id == benchmark_id)
                    .order_by(BenchmarkRun.created_at.desc())
                    .limit(min(limit, 200))
                )
            )
            .scalars()
            .all()
        )
        return list(runs)

    async def get_run(
        self, session: AsyncSession, run_id: str
    ) -> BenchmarkRun:
        r = await session.execute(
            select(BenchmarkRun).where(BenchmarkRun.id == run_id)
        )
        run = r.scalar_one_or_none()
        if run is None:
            raise NotFoundError("BenchmarkRun", run_id)
        if run.status in {"queued", "running", "pending"} and run.task_id:
            try:
                await self.finalize_run(session, run.id)
            except Exception:
                pass
            r2 = await session.execute(
                select(BenchmarkRun).where(BenchmarkRun.id == run_id)
            )
            run = r2.scalar_one()
        return run

    def compare_runs(
        self,
        current: BenchmarkRun,
        baseline: BenchmarkRun,
        *,
        score_stable_eps: float = 1.0,
    ) -> dict[str, Any]:
        """Compute regression / improvement between two runs (summary-based)."""
        cur = dict(current.summary or {})
        base = dict(baseline.summary or {})

        def _f(d: dict, key: str) -> float | None:
            v = d.get(key)
            if v is None:
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        score_c = _f(cur, "score")
        score_b = _f(base, "score")
        score_delta = None
        if score_c is not None and score_b is not None:
            score_delta = round(score_c - score_b, 4)

        dim_c = dict(cur.get("dimension_scores") or {})
        dim_b = dict(base.get("dimension_scores") or {})
        dim_keys = sorted(set(dim_c) | set(dim_b))
        dimension_deltas: dict[str, float | None] = {}
        for k in dim_keys:
            a, b = dim_c.get(k), dim_b.get(k)
            if a is None or b is None:
                dimension_deltas[k] = None
            else:
                dimension_deltas[k] = round(float(a) - float(b), 4)

        cov_c = _f(cur, "score_coverage")
        cov_b = _f(base, "score_coverage")
        rate_c = _f(cur, "success_rate")
        rate_b = _f(base, "success_rate")

        # Verdict on average score
        if score_delta is None:
            verdict = "unknown"
            headline = "缺少可比较的总分，请先 finalize 完成试跑"
        elif abs(score_delta) < score_stable_eps:
            verdict = "stable"
            headline = f"整体持平（Δscore={score_delta:+.2f}）"
        elif score_delta > 0:
            verdict = "improved"
            headline = f"整体提升（Δscore={score_delta:+.2f}）"
        else:
            verdict = "regressed"
            headline = f"整体下降（Δscore={score_delta:+.2f}）"

        # Highlight largest absolute dimension changes
        highlights: list[dict[str, Any]] = []
        for k, d in dimension_deltas.items():
            if d is None:
                continue
            highlights.append({"dimension": k, "delta": d})
        highlights.sort(key=lambda x: abs(float(x["delta"])), reverse=True)
        top_changes = highlights[:5]

        if top_changes and verdict in {"improved", "regressed", "stable"}:
            worst = min(top_changes, key=lambda x: float(x["delta"]))
            best = max(top_changes, key=lambda x: float(x["delta"]))
            if float(worst["delta"]) < -0.5:
                headline += f"；主要退化：{worst['dimension']} ({worst['delta']:+.2f})"
            elif float(best["delta"]) > 0.5:
                headline += f"；主要提升：{best['dimension']} ({best['delta']:+.2f})"

        return {
            "verdict": verdict,
            "headline": headline,
            "score_delta": score_delta,
            "current": {
                "run_id": current.id,
                "label": current.label,
                "task_id": current.task_id,
                "status": current.status,
                "summary": cur,
                "created_at": current.created_at.isoformat()
                if current.created_at
                else None,
            },
            "baseline": {
                "run_id": baseline.id,
                "label": baseline.label,
                "task_id": baseline.task_id,
                "status": baseline.status,
                "summary": base,
                "created_at": baseline.created_at.isoformat()
                if baseline.created_at
                else None,
            },
            "dimension_deltas": dimension_deltas,
            "success_rate_delta": (
                round(rate_c - rate_b, 4)
                if rate_c is not None and rate_b is not None
                else None
            ),
            "score_coverage_delta": (
                round(cov_c - cov_b, 4)
                if cov_c is not None and cov_b is not None
                else None
            ),
            "top_changes": top_changes,
            "thresholds": {"score_stable_eps": score_stable_eps},
        }

    async def leaderboard(
        self, session: AsyncSession, benchmark_id: str
    ) -> list[dict[str, Any]]:
        """Aggregate completed runs by label for leaderboard."""
        runs = (
            (
                await session.execute(
                    select(BenchmarkRun)
                    .where(BenchmarkRun.benchmark_id == benchmark_id)
                    .order_by(BenchmarkRun.created_at.desc())
                )
            )
            .scalars()
            .all()
        )

        # Finalize unfinished runs that have completed tasks (best-effort)
        for run in runs:
            if run.status in {"queued", "running", "pending"} and run.task_id:
                try:
                    await self.finalize_run(session, run.id)
                except Exception:
                    pass

        runs = (
            (
                await session.execute(
                    select(BenchmarkRun).where(
                        BenchmarkRun.benchmark_id == benchmark_id
                    )
                )
            )
            .scalars()
            .all()
        )

        by_label: dict[str, list[BenchmarkRun]] = {}
        for run in runs:
            if run.status != "completed" and not (run.summary or {}).get("score"):
                # still include if summary has metrics
                if not run.summary:
                    continue
            by_label.setdefault(run.label or "default", []).append(run)

        board: list[dict[str, Any]] = []
        for label, group in by_label.items():
            # Use latest completed-ish run per label
            group_sorted = sorted(
                group, key=lambda r: r.created_at or _now(), reverse=True
            )
            best = group_sorted[0]
            s = best.summary or {}
            board.append(
                {
                    "label": label,
                    "run_id": best.id,
                    "task_id": best.task_id,
                    "status": best.status,
                    "accuracy": s.get("accuracy"),
                    "quality": s.get("quality"),
                    "latency_ms": s.get("latency_ms"),
                    "cost": s.get("cost"),
                    "tokens": s.get("tokens"),
                    "score": s.get("score"),
                    "agent_config": best.agent_config or {},
                    "runs_count": len(group),
                    "updated_at": best.finished_at.isoformat()
                    if best.finished_at
                    else (best.created_at.isoformat() if best.created_at else None),
                }
            )

        board.sort(
            key=lambda row: (
                row["score"] is None,
                -(row["score"] or 0),
                row["latency_ms"] or 1e18,
            )
        )
        for i, row in enumerate(board, start=1):
            row["rank"] = i
        return board


_svc: BenchmarkService | None = None


def get_benchmark_service() -> BenchmarkService:
    global _svc
    if _svc is None:
        _svc = BenchmarkService()
    return _svc

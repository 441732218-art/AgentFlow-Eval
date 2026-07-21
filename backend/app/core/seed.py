"""Seed data for AgentFlow-Eval demonstration (soft-copyright / open-source demo).

Populates:
  - Demo task + suites + traces (incl. failure for Diagnosis)
  - Dimension metric scores (scorecard-aligned 40/40/20)
  - AOLS agent_logs for Dashboard / Monitoring
  - Multi-variant Experiment for /experiments compare UI

Run: ``python -m app.core.seed`` or ``python -m app.core.seed --force``
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

# Default scorecard (Phase 3) — same as judge_engine.scorecard.default_scorecard()
SAMPLE_SCORECARD = {
    "version": 1,
    "name": "default_agent_eval",
    "llm_refine": True,
    "dimensions": [
        {
            "key": "tool_accuracy",
            "label": "工具调用准确率",
            "weight": 40,
            "description": "是否按预期调用工具",
            "method": "rule_tool",
        },
        {
            "key": "answer_correctness",
            "label": "答案准确性",
            "weight": 40,
            "description": "与 expected_output 一致性",
            "method": "llm_or_lexical",
        },
        {
            "key": "reasoning_coherence",
            "label": "推理连贯性",
            "weight": 20,
            "description": "步骤是否自洽",
            "method": "llm_only",
        },
    ],
}

SAMPLE_AGENT_CONFIG = {
    "runner": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0,
    "max_iterations": 5,
    "max_tokens": 4096,
    "scorecard": SAMPLE_SCORECARD,
}

SAMPLE_AGENT_CONFIG_CANDIDATE = {
    "runner": "openai",
    "model": "gpt-4o",
    "temperature": 0,
    "max_iterations": 5,
    "max_tokens": 4096,
    "scorecard": SAMPLE_SCORECARD,
}

# Demo task: bilingual-friendly business scenarios for UI screenshots
SAMPLE_TASK = {
    "name": "客服 Agent 综合评测（Demo）",
    "description": (
        "演示用评测任务：覆盖天气、计算、差旅、邮件与常识问答；"
        "含成功/失败 Trace、三维评分与 AOLS 日志。"
        "Seed 同时写入「多变体对比」实验，打开 /experiments 即可查看。"
    ),
    "agent_config": SAMPLE_AGENT_CONFIG,
}

DEMO_EXPERIMENT_NAME = "Demo 多变体对比（mini vs 4o）"

SAMPLE_TEST_SUITES = [
    {
        "user_query": "北京今天天气怎么样？",
        "expected_output": "北京今日晴，最高气温约 25 摄氏度。",
        "expected_tools": ["get_weather"],
        "outcome": "success",
    },
    {
        "user_query": "请计算 15 × 37 等于多少？",
        "expected_output": "555",
        "expected_tools": ["calculator"],
        "outcome": "success",
    },
    {
        "user_query": "帮我预订下周一北京到上海的往返机票。",
        "expected_output": "已预订北京至上海往返航班，出发日为下周一。",
        "expected_tools": ["flight_search", "book_flight"],
        "outcome": "success",
    },
    {
        "user_query": "给 zhangsan@company.com 发邮件，主题 Meeting，正文 Hello。",
        "expected_output": "邮件已发送至 zhangsan@company.com。",
        "expected_tools": ["send_email"],
        "outcome": "success",
    },
    {
        "user_query": "法国的首都是哪里？",
        "expected_output": "法国的首都是巴黎。",
        "expected_tools": [],
        "outcome": "success",
    },
    # Failure case for Diagnosis (agent loop + tool error)
    {
        "user_query": "反复查询同一航班并重试失败的工具调用（诊断演示用例）",
        "expected_output": "应给出明确结果或失败说明",
        "expected_tools": ["flight_search"],
        "outcome": "failed",
    },
]


def _success_steps(query: str, tools: list[str]) -> list[dict]:
    steps: list[dict] = [
        {
            "type": "thought",
            "content": f"用户询问：{query[:80]}。将按预期工具执行。",
            "tokens": 40,
        },
    ]
    for tool in tools or ["final_answer"]:
        steps.append(
            {
                "type": "action",
                "tool_name": tool if tool != "final_answer" else "",
                "action": tool,
                "tool_input": query[:60],
                "content": f"call {tool}",
                "tokens": 25,
            }
        )
        steps.append(
            {
                "type": "observation",
                "content": f"{tool} ok: demo observation for seed",
                "tokens": 30,
            }
        )
    steps.append(
        {
            "type": "final_answer",
            "content": "演示种子答案（seed）",
            "tokens": 20,
        }
    )
    return steps


def _failed_loop_steps(query: str) -> list[dict]:
    """Repeated tool calls + error observations → diagnosis agent_loop / tool_failure."""
    steps: list[dict] = [
        {"type": "thought", "content": f"处理：{query[:60]}", "tokens": 50},
    ]
    for i in range(4):
        steps.append(
            {
                "type": "action",
                "tool_name": "flight_search",
                "action": "flight_search",
                "tool_input": "PEK-SHA next monday",
                "content": "retry flight_search",
                "tokens": 35 + i,
            }
        )
        steps.append(
            {
                "type": "observation",
                "content": "error: timeout connecting to flight API (rate limit 429)",
                "tokens": 20,
            }
        )
    steps.append(
        {
            "type": "final_answer",
            "content": "无法完成预订，工具反复失败",
            "tokens": 15,
        }
    )
    return steps


async def seed_database(async_session_factory, *, force: bool = False) -> None:
    """Insert seed data into the database.

    Args:
        async_session_factory: SQLAlchemy async session factory.
        force: If True, insert demo task even when other tasks already exist
            (skips only when a demo-named task is present).
    """
    from sqlalchemy import select, func

    from app.models.agent_log import AgentLog
    from app.models.metric_score import MetricScore
    from app.models.task import Task, TaskStatus
    from app.models.test_suite import TestSuite
    from app.models.trace import Trace, TraceStatus

    async with async_session_factory() as session:
        if not force:
            result = await session.execute(select(func.count(Task.id)))
            count = result.scalar() or 0
            if count > 0:
                print(f"Database already has {count} tasks; skipping seed.")
                print("Hint: use --force to add demo task anyway.")
                return
        else:
            existing = await session.execute(
                select(Task).where(Task.name == SAMPLE_TASK["name"]).limit(1)
            )
            existing_task = existing.scalar_one_or_none()
            if existing_task is not None:
                print("Demo task already exists; ensuring experiment seed only.")
                exp_id, labels = await _seed_experiment_pair(
                    session,
                    base_task_id=existing_task.id,
                    now=datetime.now(timezone.utc),
                )
                await session.commit()
                if exp_id:
                    print(f"  Experiment: {DEMO_EXPERIMENT_NAME} ({exp_id})")
                    print(f"  Variants  : {', '.join(labels)}")
                    print("Next: open /experiments")
                return

        now = datetime.now(timezone.utc)
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            name=SAMPLE_TASK["name"],
            description=SAMPLE_TASK["description"],
            agent_config=SAMPLE_TASK["agent_config"],
            status=TaskStatus.COMPLETED,
            created_by="demo",
        )
        session.add(task)
        await session.flush()

        suite_ids: list[str] = []
        trace_ids: list[str] = []
        log_rows = 0

        for idx, suite_data in enumerate(SAMPLE_TEST_SUITES):
            suite_id = str(uuid4())
            suite = TestSuite(
                id=suite_id,
                task_id=task.id,
                user_query=suite_data["user_query"],
                expected_output=suite_data["expected_output"],
                expected_tools=suite_data["expected_tools"],
            )
            session.add(suite)
            suite_ids.append(suite_id)
            await session.flush()

            failed = suite_data.get("outcome") == "failed"
            steps = (
                _failed_loop_steps(suite_data["user_query"])
                if failed
                else _success_steps(
                    suite_data["user_query"],
                    list(suite_data.get("expected_tools") or []),
                )
            )
            tokens = sum(int(s.get("tokens") or 0) for s in steps)
            # Stagger timestamps across recent days for dashboard series
            created = now - timedelta(
                days=(len(SAMPLE_TEST_SUITES) - idx) % 6, hours=idx
            )

            trace_id = str(uuid4())
            tr = Trace(
                id=trace_id,
                test_suite_id=suite_id,
                user_query=suite_data["user_query"],
                steps=steps,
                total_tokens=tokens,
                prompt_tokens=int(tokens * 0.6),
                completion_tokens=int(tokens * 0.4),
                response_time_ms=800 + idx * 120 + (2000 if failed else 0),
                status=TraceStatus.FAILED if failed else TraceStatus.SUCCESS,
                cost=round(tokens * 0.000002, 6),
                agent_version="demo-seed-1.0",
                model_version="gpt-4o-mini",
            )
            # created_at may be server-default; set if column allows
            if hasattr(tr, "created_at"):
                try:
                    tr.created_at = created  # type: ignore[assignment]
                except Exception:
                    pass
            session.add(tr)
            trace_ids.append(trace_id)
            await session.flush()

            for metric_name, score, reason in _dimension_scores(
                failed=failed, idx=idx, variant="baseline"
            ):
                session.add(
                    MetricScore(
                        id=str(uuid4()),
                        trace_id=trace_id,
                        metric_name=metric_name,
                        score=score,
                        reason=reason,
                        confidence=0.75 if not failed else 0.55,
                    )
                )

            # AOLS events for Monitoring + Dashboard log cards
            events = [
                ("info", "evaluation.running", {"suite_index": idx}),
                ("info", "agent.started", {"model": "gpt-4o-mini"}),
                (
                    "info" if not failed else "error",
                    "agent.completed" if not failed else "agent.failed",
                    {"tokens": tokens, "latency_ms": tr.response_time_ms},
                ),
                (
                    "info",
                    "llm.request",
                    {"tokens": tokens, "latency_ms": 200 + idx * 10},
                ),
            ]
            if failed:
                events.append(
                    (
                        "error",
                        "tool.failed",
                        {"tool": "flight_search", "error": "timeout 429"},
                    )
                )
            else:
                events.append(
                    (
                        "info",
                        "tool.completed",
                        {"tool": (suite_data.get("expected_tools") or ["none"])[0]},
                    )
                )

            for level, event, payload in events:
                session.add(
                    AgentLog(
                        id=str(uuid4()),
                        level=level,
                        event=event,
                        service="agentflow-api",
                        trace_id=trace_id[:32],
                        task_id=task_id,
                        payload={
                            "seed": True,
                            "total_tokens": tokens,
                            "latency_ms": tr.response_time_ms,
                            **payload,
                        },
                    )
                )
                log_rows += 1

        # Extra synthetic log volume for statistics charts (recent window)
        for d in range(7):
            for k in range(3):
                session.add(
                    AgentLog(
                        id=str(uuid4()),
                        level="info" if k % 3 else "warning",
                        event="http.request" if k else "evaluation.suite_complete",
                        service="agentflow-api",
                        trace_id=f"seed-day-{d}",
                        task_id=task_id,
                        payload={
                            "seed": True,
                            "total_tokens": 100 + d * 10 + k,
                            "latency_ms": 50 + k * 15,
                            "day_offset": d,
                        },
                    )
                )
                log_rows += 1

        # --- Multi-variant experiment (compare UI) ---
        exp_id, run_labels = await _seed_experiment_pair(
            session,
            base_task_id=task_id,
            now=now,
        )

        await session.commit()
        print(f"Seeded demo task with {len(SAMPLE_TEST_SUITES)} suites.")
        print(f"  Task name : {SAMPLE_TASK['name']}")
        print(f"  Task id   : {task_id}")
        print(f"  Traces    : {len(trace_ids)} (incl. 1 failed for Diagnosis)")
        print(f"  AgentLogs : {log_rows}")
        print(f"  Scorecard : default 40/40/20 on agent_config")
        if exp_id:
            print(f"  Experiment: {DEMO_EXPERIMENT_NAME}")
            print(f"  Exp id    : {exp_id}")
            print(f"  Variants  : {', '.join(run_labels)}")
        print(
            "Next: /dashboard · /experiments · demo task Trace + ScoreCard · /diagnosis"
        )


def _dimension_scores(
    *,
    failed: bool,
    idx: int,
    variant: str = "baseline",
) -> list[tuple[str, float, str]]:
    """Scorecard-aligned seed scores (tool/answer/coherence)."""
    # candidate (gpt-4o) slightly better for demo compare narrative
    boost = 3.0 if variant == "candidate" else 0.0
    if failed:
        return [
            ("tool_accuracy", 12.0, "seed: tool loop / timeout"),
            ("answer_correctness", 15.0, "seed: incomplete answer"),
            ("reasoning_coherence", 8.0, "seed: repeated steps"),
        ]
    tool = min(40.0, max(0.0, 36.0 - idx * 0.8 + boost))
    ans = min(40.0, max(0.0, 34.0 - idx * 0.5 + boost))
    coh = min(20.0, max(0.0, 17.5 - idx * 0.3 + boost * 0.5))
    return [
        ("tool_accuracy", round(tool, 1), "seed demo"),
        ("answer_correctness", round(ans, 1), "seed demo"),
        ("reasoning_coherence", round(coh, 1), "seed demo"),
    ]


async def _seed_variant_task(
    session,
    *,
    label: str,
    agent_config: dict,
    snapshot: list[dict],
    variant: str,
    model_version: str,
) -> str:
    """Materialize one completed variant task with suites/traces/metrics."""
    from app.models.metric_score import MetricScore
    from app.models.task import Task, TaskStatus
    from app.models.test_suite import TestSuite
    from app.models.trace import Trace, TraceStatus

    task_id = str(uuid4())
    session.add(
        Task(
            id=task_id,
            name=f"Demo 对比变体 · {label}",
            description=f"Seed 变体 {label}，与其它变体共享相同用例快照。",
            agent_config=agent_config,
            status=TaskStatus.COMPLETED,
            created_by="demo",
        )
    )
    await session.flush()

    for idx, case in enumerate(snapshot):
        suite_id = str(uuid4())
        session.add(
            TestSuite(
                id=suite_id,
                task_id=task_id,
                user_query=case["user_query"],
                expected_output=case["expected_output"],
                expected_tools=case["expected_tools"],
            )
        )
        await session.flush()
        steps = _success_steps(
            case["user_query"], list(case.get("expected_tools") or [])
        )
        tokens = sum(int(s.get("tokens") or 0) for s in steps)
        # candidate slightly more tokens/latency for cost narrative
        token_mul = 1.15 if variant == "candidate" else 1.0
        tokens = int(tokens * token_mul)
        tid = str(uuid4())
        session.add(
            Trace(
                id=tid,
                test_suite_id=suite_id,
                user_query=case["user_query"],
                steps=steps,
                total_tokens=tokens,
                prompt_tokens=int(tokens * 0.6),
                completion_tokens=int(tokens * 0.4),
                response_time_ms=int(
                    (750 + idx * 90) * (1.1 if variant == "candidate" else 1.0)
                ),
                status=TraceStatus.SUCCESS,
                cost=round(tokens * 0.0000025, 6),
                agent_version="demo-seed-1.0",
                model_version=model_version,
            )
        )
        await session.flush()
        for metric_name, score, reason in _dimension_scores(
            failed=False, idx=idx, variant=variant
        ):
            session.add(
                MetricScore(
                    id=str(uuid4()),
                    trace_id=tid,
                    metric_name=metric_name,
                    score=score,
                    reason=reason,
                    confidence=0.8,
                )
            )
    return task_id


async def _seed_experiment_pair(session, *, base_task_id: str, now: datetime):
    """Create two fair variant tasks + Experiment for /experiments compare."""
    from app.models.experiment import Experiment, ExperimentRun
    from sqlalchemy import select

    _ = now
    existing = await session.execute(
        select(Experiment).where(Experiment.name == DEMO_EXPERIMENT_NAME).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        print("Demo experiment already exists; skip experiment seed.")
        return None, []

    snapshot = [
        {
            "user_query": s["user_query"],
            "expected_output": s["expected_output"],
            "expected_tools": list(s.get("expected_tools") or []),
        }
        for s in SAMPLE_TEST_SUITES
        if s.get("outcome") != "failed"
    ][:3]

    baseline_id = await _seed_variant_task(
        session,
        label="gpt-4o-mini",
        agent_config=SAMPLE_AGENT_CONFIG,
        snapshot=snapshot,
        variant="baseline",
        model_version="gpt-4o-mini",
    )
    candidate_id = await _seed_variant_task(
        session,
        label="gpt-4o",
        agent_config=SAMPLE_AGENT_CONFIG_CANDIDATE,
        snapshot=snapshot,
        variant="candidate",
        model_version="gpt-4o",
    )

    exp_id = str(uuid4())
    session.add(
        Experiment(
            id=exp_id,
            name=DEMO_EXPERIMENT_NAME,
            description=(
                "Seed 演示：同一套 3 条用例，对比 gpt-4o-mini 与 gpt-4o。"
                "打开「对比实验」查看 Best / 维度分 / Token / 耗时。"
            ),
            base_task_id=base_task_id,
            suite_snapshot=snapshot,
            created_by="demo",
        )
    )
    await session.flush()
    session.add(
        ExperimentRun(
            id=str(uuid4()),
            experiment_id=exp_id,
            task_id=baseline_id,
            label="gpt-4o-mini",
            agent_config=SAMPLE_AGENT_CONFIG,
        )
    )
    session.add(
        ExperimentRun(
            id=str(uuid4()),
            experiment_id=exp_id,
            task_id=candidate_id,
            label="gpt-4o",
            agent_config=SAMPLE_AGENT_CONFIG_CANDIDATE,
        )
    )
    return exp_id, ["gpt-4o-mini", "gpt-4o"]


def main() -> None:
    import argparse
    import asyncio
    import sys

    parser = argparse.ArgumentParser(description="Seed AgentFlow-Eval demo data")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Insert demo task even if other tasks already exist",
    )
    args = parser.parse_args()

    try:
        from app.core.dependencies import async_session_factory
    except Exception as exc:  # pragma: no cover
        print("Failed to import app dependencies:", exc, file=sys.stderr)
        print(
            "Run from backend/ with venv activated and .env configured.",
            file=sys.stderr,
        )
        sys.exit(1)

    asyncio.run(seed_database(async_session_factory, force=args.force))


if __name__ == "__main__":
    main()

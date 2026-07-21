"""Seed data for AgentFlow-Eval demonstration (soft-copyright / open-source demo).

Populates tasks, suites, traces (incl. failure for Diagnosis), metric scores,
and AOLS ``agent_logs`` so Dashboard / Monitoring / Diagnosis are non-empty
after ``python -m app.core.seed``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

SAMPLE_AGENT_CONFIG = {
    "model": "gpt-4o-mini",
    "temperature": 0,
    "max_iterations": 5,
    "max_tokens": 4096,
}

# Demo task: bilingual-friendly business scenarios for UI screenshots
SAMPLE_TASK = {
    "name": "客服 Agent 综合评测（Demo）",
    "description": (
        "演示用评测任务：覆盖天气查询、数值计算、差旅预订、邮件发送与常识问答，"
        "用于本地启动后的界面展示与流水线验证。可通过 python -m app.core.seed 写入。"
        "含成功/失败 Trace 与 AOLS 日志，便于驾驶舱与诊断页演示。"
    ),
    "agent_config": SAMPLE_AGENT_CONFIG,
}

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
            if existing.scalar_one_or_none() is not None:
                print("Demo task already exists; skipping seed.")
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

            score = 42.0 if failed else 88.0 - idx * 1.5
            session.add(
                MetricScore(
                    id=str(uuid4()),
                    trace_id=trace_id,
                    metric_name="overall",
                    score=max(0.0, score),
                    reason="seed demo score" if not failed else "tool loop / timeout",
                    confidence=0.75 if not failed else 0.55,
                )
            )
            session.add(
                MetricScore(
                    id=str(uuid4()),
                    trace_id=trace_id,
                    metric_name="tool_accuracy",
                    score=30.0 if failed else 92.0,
                    reason="seed",
                    confidence=0.7,
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

        await session.commit()
        print(f"Seeded demo task with {len(SAMPLE_TEST_SUITES)} suites.")
        print(f"  Task name : {SAMPLE_TASK['name']}")
        print(f"  Task id   : {task_id}")
        print(f"  Traces    : {len(trace_ids)} (incl. 1 failed for Diagnosis)")
        print(f"  AgentLogs : {log_rows}")
        print(
            "Next: open /dashboard /diagnosis /monitoring — cards should be non-empty."
        )


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

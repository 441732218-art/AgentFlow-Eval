"""Seed data for AgentFlow-Eval demonstration (soft-copyright / open-source demo)."""

from __future__ import annotations

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
    ),
    "agent_config": SAMPLE_AGENT_CONFIG,
}

SAMPLE_TEST_SUITES = [
    {
        "user_query": "北京今天天气怎么样？",
        "expected_output": "北京今日晴，最高气温约 25 摄氏度。",
        "expected_tools": ["get_weather"],
    },
    {
        "user_query": "请计算 15 × 37 等于多少？",
        "expected_output": "555",
        "expected_tools": ["calculator"],
    },
    {
        "user_query": "帮我预订下周一北京到上海的往返机票。",
        "expected_output": "已预订北京至上海往返航班，出发日为下周一。",
        "expected_tools": ["flight_search", "book_flight"],
    },
    {
        "user_query": "给 zhangsan@company.com 发邮件，主题 Meeting，正文 Hello。",
        "expected_output": "邮件已发送至 zhangsan@company.com。",
        "expected_tools": ["send_email"],
    },
    {
        "user_query": "法国的首都是哪里？",
        "expected_output": "法国的首都是巴黎。",
        "expected_tools": [],
    },
]


async def seed_database(async_session_factory, *, force: bool = False) -> None:
    """Insert seed data into the database.

    Args:
        async_session_factory: SQLAlchemy async session factory.
        force: If True, insert demo task even when other tasks already exist
            (skips only when a demo-named task is present).
    """
    from sqlalchemy import select, func

    from app.models.task import Task, TaskStatus
    from app.models.test_suite import TestSuite

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

        task = Task(
            id=str(uuid4()),
            name=SAMPLE_TASK["name"],
            description=SAMPLE_TASK["description"],
            agent_config=SAMPLE_TASK["agent_config"],
            status=TaskStatus.CREATED,
            created_by="demo",
        )
        session.add(task)
        await session.flush()

        for suite_data in SAMPLE_TEST_SUITES:
            suite = TestSuite(
                task_id=task.id,
                user_query=suite_data["user_query"],
                expected_output=suite_data["expected_output"],
                expected_tools=suite_data["expected_tools"],
            )
            session.add(suite)

        await session.commit()
        print(f"Seeded 1 demo task with {len(SAMPLE_TEST_SUITES)} test suites.")
        print(f"  Task name: {SAMPLE_TASK['name']}")


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
        print("Run from backend/ with venv activated and .env configured.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(seed_database(async_session_factory, force=args.force))


if __name__ == "__main__":
    main()

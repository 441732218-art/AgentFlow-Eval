"""Seed data for AgentFlow-Eval demonstration."""

from uuid import uuid4

SAMPLE_AGENT_CONFIG = {
    "model": "gpt-4o-mini",
    "temperature": 0,
    "max_iterations": 5,
    "max_tokens": 4096,
}

SAMPLE_TASK = {
    "name": "Customer Support Agent Evaluation",
    "description": "Evaluate a customer support agent on common business queries.",
    "agent_config": SAMPLE_AGENT_CONFIG,
}

SAMPLE_TEST_SUITES = [
    {
        "user_query": "What is the weather in Beijing today?",
        "expected_output": "The weather in Beijing is sunny with a high of 25 degrees Celsius.",
        "expected_tools": ["get_weather"],
    },
    {
        "user_query": "Calculate 15 * 37",
        "expected_output": "555",
        "expected_tools": ["calculator"],
    },
    {
        "user_query": "Book a round-trip flight from Beijing to Shanghai for next Monday.",
        "expected_output": "Flight booked: Beijing to Shanghai, round-trip, next Monday.",
        "expected_tools": ["flight_search", "book_flight"],
    },
    {
        "user_query": "Send an email to zhangsan@company.com with subject Meeting and body Hello.",
        "expected_output": "Email sent to zhangsan@company.com.",
        "expected_tools": ["send_email"],
    },
    {
        "user_query": "What is the capital of France?",
        "expected_output": "The capital of France is Paris.",
        "expected_tools": [],
    },
]


async def seed_database(async_session_factory):
    """Insert seed data into the database.

    Args:
        async_session_factory: SQLAlchemy async session factory.
    """
    from sqlalchemy import select, func
    from app.models.task import Task, TaskStatus
    from app.models.test_suite import TestSuite

    async with async_session_factory() as session:
        result = await session.execute(select(func.count(Task.id)))
        count = result.scalar() or 0
        if count > 0:
            print(f"Database already has {count} tasks; skipping seed.")
            return

        task = Task(
            id=str(uuid4()),
            name=SAMPLE_TASK["name"],
            description=SAMPLE_TASK["description"],
            agent_config=SAMPLE_TASK["agent_config"],
            status=TaskStatus.CREATED,
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
        print(f"Seeded 1 task with {len(SAMPLE_TEST_SUITES)} test suites.")


if __name__ == "__main__":
    import asyncio
    from app.core.dependencies import async_session_factory
    asyncio.run(seed_database(async_session_factory))

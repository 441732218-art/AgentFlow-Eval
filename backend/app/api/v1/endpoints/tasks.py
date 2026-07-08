# (c) 2026 AgentFlow-Eval
"""Task CRUD API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse
from app.utils.exceptions import NotFoundError, error_response

router = APIRouter()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Get paginated list of evaluation tasks."""
    query = select(Task)
    count_query = select(func.count(Task.id))

    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)

    query = query.order_by(Task.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    result = await session.execute(query)
    tasks = result.scalars().all()

    items = []
    for task in tasks:
        suite_count_result = await session.execute(
            select(func.count(TestSuite.id)).where(TestSuite.task_id == task.id)
        )
        suite_count = suite_count_result.scalar() or 0
        items.append(TaskResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            status=task.status.value,
            agent_config=task.agent_config,
            created_at=task.created_at,
            updated_at=task.updated_at,
            test_suite_count=suite_count,
        ))

    return TaskListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new evaluation task."""
    task = Task(
        name=body.name,
        description=body.description,
        agent_config=body.agent_config,
        status=TaskStatus.PENDING,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        status=task.status.value,
        agent_config=task.agent_config,
        created_at=task.created_at,
        updated_at=task.updated_at,
        test_suite_count=0,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Get task details by ID."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task", task_id)

    suite_count_result = await session.execute(
        select(func.count(TestSuite.id)).where(TestSuite.task_id == task.id)
    )
    suite_count = suite_count_result.scalar() or 0

    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        status=task.status.value,
        agent_config=task.agent_config,
        created_at=task.created_at,
        updated_at=task.updated_at,
        test_suite_count=suite_count,
    )


@router.delete("/{task_id}", status_code=200)
async def delete_task(
    task_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a task and its associated records."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task", task_id)

    await session.delete(task)
    await session.commit()
    return {"message": "Task deleted", "task_id": task_id}


@router.post("/{task_id}/execute")
async def execute_task(
    task_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger async execution of the evaluation task."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task", task_id)

    from app.core.celery_app.tasks import run_full_evaluation

    task.status = TaskStatus.RUNNING
    await session.commit()

    run_full_evaluation.delay(task_id)

    return {
        "task_id": task_id,
        "status": "running",
        "message": "Task submitted to execution queue",
    }

@router.post("/{task_id}/test-suites", status_code=201)
async def create_test_suites(
    task_id: str,
    suites: list[dict],
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Batch-create test suites for a task."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task", task_id)

    count = 0
    for item in suites:
        if not item.get("user_query"):
            continue
        suite = TestSuite(
            task_id=task_id,
            user_query=str(item.get("user_query", "")),
            expected_output=str(item.get("expected_output", "")),
            expected_tools=item.get("expected_tools", []),
            extra_metadata=item.get("extra_metadata"),
        )
        session.add(suite)
        count += 1

    await session.commit()
    return {"task_id": task_id, "created": count}

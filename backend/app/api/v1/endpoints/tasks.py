# (c) 2026 AgentFlow-Eval
"""Task CRUD API endpoints with optional actor tenancy."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit
from app.core.dependencies import get_db
from app.core.tenancy import apply_owner_filter, ensure_task_access
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse
from app.utils.exceptions import NotFoundError

router = APIRouter()


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", None) or "anonymous"


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


async def _task_to_response(session: AsyncSession, task: Task) -> TaskResponse:
    suite_count_result = await session.execute(
        select(func.count(TestSuite.id)).where(TestSuite.task_id == task.id)
    )
    suite_count = suite_count_result.scalar() or 0
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        status=task.status.value,
        agent_config=task.agent_config or {},
        celery_task_id=task.celery_task_id,
        is_archived=bool(getattr(task, "is_archived", False)),
        created_by=getattr(task, "created_by", None) or "anonymous",
        created_at=task.created_at,
        updated_at=task.updated_at,
        test_suite_count=suite_count,
    )


async def _load_task(
    session: AsyncSession,
    task_id: str,
    actor: str,
) -> Task:
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    return ensure_task_access(task, actor, task_id)


def _parse_expected_tools(raw: Any) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except json.JSONDecodeError:
            pass
    return [t.strip() for t in text.split("|") if t.strip()] or [
        t.strip() for t in text.split(",") if t.strip()
    ]


def _suites_from_items(task_id: str, items: list[dict]) -> list[TestSuite]:
    suites: list[TestSuite] = []
    for item in items:
        if not item.get("user_query"):
            continue
        suites.append(
            TestSuite(
                task_id=task_id,
                user_query=str(item.get("user_query", "")),
                expected_output=str(item.get("expected_output", "")),
                expected_tools=_parse_expected_tools(item.get("expected_tools")),
                extra_metadata=item.get("extra_metadata"),
            )
        )
    return suites


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    include_archived: bool = Query(False, description="Include archived tasks"),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Get paginated list of evaluation tasks (scoped by actor when tenancy on)."""
    actor = _actor(request)
    query = select(Task)
    count_query = select(func.count(Task.id))

    query = apply_owner_filter(query, actor)
    count_query = apply_owner_filter(count_query, actor)

    if not include_archived:
        query = query.where(Task.is_archived.is_(False))
        count_query = count_query.where(Task.is_archived.is_(False))

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

    items = [await _task_to_response(session, task) for task in tasks]
    return TaskListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new evaluation task owned by the current actor."""
    actor = _actor(request)
    task = Task(
        name=body.name,
        description=body.description,
        agent_config=body.agent_config,
        status=TaskStatus.CREATED,
        created_by=actor,
    )
    session.add(task)
    await session.flush()
    await write_audit(
        session,
        action="task.create",
        resource_type="task",
        resource_id=task.id,
        actor=actor,
        detail={"name": task.name, "created_by": actor},
        request_id=_request_id(request),
        ip=_client_ip(request),
    )
    await session.commit()
    await session.refresh(task)
    return await _task_to_response(session, task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Get task details by ID (owner-scoped when tenancy on)."""
    task = await _load_task(session, task_id, _actor(request))
    return await _task_to_response(session, task)


@router.delete("/{task_id}", status_code=200)
async def delete_task(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a task and its associated records."""
    actor = _actor(request)
    task = await _load_task(session, task_id, actor)

    await write_audit(
        session,
        action="task.delete",
        resource_type="task",
        resource_id=task_id,
        actor=actor,
        detail={"name": task.name},
        request_id=_request_id(request),
        ip=_client_ip(request),
    )
    await session.delete(task)
    await session.commit()
    return {"message": "Task deleted", "task_id": task_id}


@router.post("/{task_id}/execute")
async def execute_task(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger async execution of the evaluation task."""
    actor = _actor(request)
    task = await _load_task(session, task_id, actor)

    if not task.status.can_transition_to(TaskStatus.QUEUED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot execute task in '{task.status.value}' state. "
                   f"Only tasks in 'created' state can be executed.",
        )

    from app.core.celery_app.tasks import run_full_evaluation

    prev_status = task.status.value
    task.status = TaskStatus.QUEUED
    await session.flush()

    celery_result = run_full_evaluation.delay(task_id)
    task.celery_task_id = celery_result.id
    await write_audit(
        session,
        action="task.execute",
        resource_type="task",
        resource_id=task_id,
        actor=actor,
        detail={"celery_task_id": celery_result.id},
        request_id=_request_id(request),
        ip=_client_ip(request),
    )
    await session.commit()

    try:
        from app.core.events import publish_task_status

        publish_task_status(
            task.id,
            task.name,
            TaskStatus.QUEUED.value,
            prev_status=prev_status,
            actor=actor,
        )
    except Exception:
        pass

    return {
        "task_id": task_id,
        "status": "queued",
        "celery_task_id": celery_result.id,
        "message": "Task submitted to execution queue",
    }


@router.post("/{task_id}/test-suites", status_code=201)
async def create_test_suites(
    task_id: str,
    suites: list[dict],
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Batch-create test suites for a task."""
    await _load_task(session, task_id, _actor(request))

    created_suites = _suites_from_items(task_id, suites)
    for suite in created_suites:
        session.add(suite)

    await session.commit()
    return {"task_id": task_id, "created": len(created_suites)}


@router.post("/{task_id}/test-suites/upload", status_code=201)
async def upload_test_suites(
    task_id: str,
    request: Request,
    file: UploadFile = File(..., description="CSV or JSON test suite file"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Upload CSV/JSON file to batch-import test suites."""
    actor = _actor(request)
    await _load_task(session, task_id, actor)

    filename = (file.filename or "").lower()
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded") from exc

    items: list[dict] = []
    if filename.endswith(".json") or text.lstrip().startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
        if not isinstance(data, list):
            raise HTTPException(status_code=400, detail="JSON must be an array of test cases")
        items = [x for x in data if isinstance(x, dict)]
    elif filename.endswith(".csv") or "," in text.splitlines()[0]:
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or "user_query" not in reader.fieldnames:
            raise HTTPException(
                status_code=400,
                detail="CSV must include a 'user_query' column "
                       "(optional: expected_output, expected_tools)",
            )
        items = list(reader)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload .csv or .json",
        )

    created_suites = _suites_from_items(task_id, items)
    if not created_suites:
        raise HTTPException(status_code=400, detail="No valid test cases found in file")

    for suite in created_suites:
        session.add(suite)
    await write_audit(
        session,
        action="task.upload_suites",
        resource_type="task",
        resource_id=task_id,
        actor=actor,
        detail={"filename": file.filename, "created": len(created_suites)},
        request_id=_request_id(request),
        ip=_client_ip(request),
    )
    await session.commit()

    return {
        "task_id": task_id,
        "created": len(created_suites),
        "filename": file.filename,
        "message": f"Imported {len(created_suites)} test suite(s)",
    }


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel a running evaluation task."""
    actor = _actor(request)
    task = await _load_task(session, task_id, actor)

    if not task.status.can_transition_to(TaskStatus.CANCELLED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel task in '{task.status.value}' state.",
        )

    if task.celery_task_id:
        from app.core.celery_app.celery import celery_app as celery
        celery.control.revoke(task.celery_task_id, terminate=True, signal="SIGTERM")

    prev_status = task.status.value
    task.status = TaskStatus.CANCELLED
    await write_audit(
        session,
        action="task.cancel",
        resource_type="task",
        resource_id=task_id,
        actor=actor,
        request_id=_request_id(request),
        ip=_client_ip(request),
    )
    await session.commit()

    try:
        from app.core.events import publish_task_status

        publish_task_status(
            task.id,
            task.name,
            TaskStatus.CANCELLED.value,
            prev_status=prev_status,
            actor=actor,
        )
    except Exception:
        pass

    return {
        "task_id": task_id,
        "status": "cancelled",
        "message": "Task has been cancelled",
    }


@router.post("/{task_id}/archive")
async def archive_task(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Soft-archive a terminal-state task (hidden from default list)."""
    actor = _actor(request)
    task = await _load_task(session, task_id, actor)

    terminal_states = {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.TIMEOUT,
    }
    if task.status not in terminal_states:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot archive task in '{task.status.value}' state. "
                   f"Only terminal-state tasks can be archived.",
        )

    task.is_archived = True
    await write_audit(
        session,
        action="task.archive",
        resource_type="task",
        resource_id=task_id,
        actor=actor,
        request_id=_request_id(request),
        ip=_client_ip(request),
    )
    await session.commit()

    return {
        "task_id": task_id,
        "status": task.status.value,
        "is_archived": True,
        "message": "Task archived successfully",
    }


@router.post("/{task_id}/unarchive")
async def unarchive_task(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Restore an archived task to the default list."""
    actor = _actor(request)
    task = await _load_task(session, task_id, actor)

    task.is_archived = False
    await session.commit()

    return {
        "task_id": task_id,
        "status": task.status.value,
        "is_archived": False,
        "message": "Task unarchived successfully",
    }

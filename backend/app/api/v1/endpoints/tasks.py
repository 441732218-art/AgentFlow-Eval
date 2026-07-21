# (c) 2026 AgentFlow-Eval
"""Task CRUD API endpoints with optional actor tenancy."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit
from app.core.db.queries import count_suites_for_task
from app.core.dependencies import get_db
from app.core.rbac import Permission, get_request_role, require_permission
from app.core.tenancy import ensure_task_access
from app.models.task import Task, TaskStatus
from app.models.test_suite import TestSuite
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse

router = APIRouter()


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", None) or "anonymous"


def _role(request: Request) -> str:
    role = get_request_role(request)
    return role.value


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


async def _invalidate_task_caches(task_id: str, actor: str) -> None:
    """Best-effort multi-layer cache invalidation after task mutations."""
    try:
        from app.core.cache.invalidation import invalidate_task

        await invalidate_task(task_id, actor=actor)
    except Exception:
        pass


def _task_to_response_with_count(task: Task, suite_count: int) -> TaskResponse:
    """Build TaskResponse without extra queries."""
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


async def _task_to_response(session: AsyncSession, task: Task) -> TaskResponse:
    """Detail path: one COUNT query for suite_count."""
    suite_count = await count_suites_for_task(session, task.id)
    return _task_to_response_with_count(task, suite_count)


async def _load_task(
    session: AsyncSession,
    task_id: str,
    actor: str,
    *,
    role: str | None = None,
) -> Task:
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    return ensure_task_access(task, actor, task_id, role=role)


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
@require_permission(Permission.TASK_READ)
async def list_tasks(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    include_archived: bool = Query(False, description="Include archived tasks"),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Get paginated list of evaluation tasks (scoped by actor when tenancy on).

    Cached 30s with version-based invalidation on task mutations.
    """
    from app.core.cache.services import get_cached_task_list
    from app.core.tenant_context import extract_tenant_header, resolve_tenant_context
    from app.schemas.task import TaskResponse as TR

    actor = _actor(request)
    role = _role(request)
    await resolve_tenant_context(
        session,
        actor=actor,
        header_value=extract_tenant_header(request),
        system_role=role,
    )
    payload = await get_cached_task_list(
        session,
        actor=actor,
        role=role,
        page=page,
        page_size=page_size,
        status=status,
        include_archived=include_archived,
    )
    items = [TR(**item) for item in payload["items"]]
    return TaskListResponse(
        items=items,
        total=payload["total"],
        page=payload["page"],
        page_size=payload["page_size"],
    )


@router.post("", response_model=TaskResponse, status_code=201)
@require_permission(Permission.TASK_CREATE)
async def create_task(
    body: TaskCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new evaluation task owned by the current actor."""
    actor = _actor(request)
    from app.core.tenant_context import (
        current_tenant_id,
        extract_tenant_header,
        resolve_tenant_context,
    )

    role = getattr(request.state, "role", None)
    role_s = role.value if hasattr(role, "value") else str(role or "")
    await resolve_tenant_context(
        session,
        actor=actor,
        header_value=extract_tenant_header(request),
        system_role=role_s,
    )
    tenant_id = current_tenant_id()

    task = Task(
        name=body.name,
        description=body.description,
        agent_config=body.agent_config,
        status=TaskStatus.CREATED,
        created_by=actor,
        tenant_id=tenant_id,
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
    try:
        from app.core.observability.metrics import observe_task_created

        observe_task_created(tenant=actor, agent_config=task.agent_config or {})
    except Exception:
        pass
    try:
        from app.core.cache.invalidation import (
            invalidate_dashboard,
            invalidate_task_lists,
        )
        from app.core.cache.services import set_cached_task_detail

        # Write-through detail + bump list/dashboard versions
        await set_cached_task_detail(task, suite_count=0)
        await invalidate_task_lists(actor)
        await invalidate_dashboard(actor)
    except Exception:
        pass
    return await _task_to_response(session, task)


@router.get("/{task_id}", response_model=TaskResponse)
@require_permission(Permission.TASK_READ)
async def get_task(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """Get task details by ID (owner-scoped when tenancy on). Cached 5 min."""
    from app.core.cache.services import get_cached_task_detail

    task = await _load_task(
        session, task_id, _actor(request), role=_role(request)
    )
    payload = await get_cached_task_detail(session, task)
    return TaskResponse(**payload)


@router.delete("/{task_id}", status_code=200)
@require_permission(Permission.TASK_DELETE)
async def delete_task(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a task and its associated records."""
    actor = _actor(request)
    task = await _load_task(session, task_id, actor, role=_role(request))

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
    try:
        from app.core.cache.invalidation import invalidate_task

        await invalidate_task(task_id, actor=actor)
    except Exception:
        pass
    return {"message": "Task deleted", "task_id": task_id}


@router.post("/{task_id}/execute")
@require_permission(Permission.TASK_EXECUTE)
async def execute_task(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger async execution of the evaluation task."""
    actor = _actor(request)
    task = await _load_task(session, task_id, actor, role=_role(request))

    if not task.status.can_transition_to(TaskStatus.QUEUED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot execute task in '{task.status.value}' state. "
                   f"Only tasks in 'created' state can be executed.",
        )

    # SaaS quota gate (no-op when BILLING_ENABLED=false)
    try:
        from app.core.billing.service import QuotaExceededError, get_billing_service

        await get_billing_service().ensure_task_quota(session, actor)
    except QuotaExceededError:
        raise
    except Exception:
        pass

    from app.core.profiles import get_task_queue
    from app.core.observability.tracing import get_trace_id

    prev_status = task.status.value
    task.status = TaskStatus.QUEUED
    await session.flush()

    # Pluggable queue — pass TraceID into worker for full-chain correlation
    queue = get_task_queue()
    trace_id = get_trace_id() or _request_id(request)
    enq = queue.enqueue(
        "run_full_evaluation",
        args=(task_id,),
        kwargs={"_trace_id": trace_id} if trace_id else None,
    )
    task.celery_task_id = enq.task_id

    # Meter task execution (best-effort)
    try:
        from app.core.billing.service import get_billing_service

        await get_billing_service().record_usage(
            session,
            actor=actor,
            metric="task",
            quantity=1,
            ref_type="task",
            ref_id=task_id,
            trace_id=trace_id or None,
        )
    except Exception:
        pass
    await write_audit(
        session,
        action="task.execute",
        resource_type="task",
        resource_id=task_id,
        actor=actor,
        detail={
            "celery_task_id": enq.task_id,
            "queue_backend": enq.backend,
            "eager": enq.eager,
            "trace_id": trace_id,
        },
        request_id=trace_id or _request_id(request),
        ip=_client_ip(request),
    )
    await session.commit()
    await _invalidate_task_caches(task_id, actor)

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
        "celery_task_id": enq.task_id,
        "queue_backend": enq.backend,
        "message": "Task submitted to execution queue",
    }


@router.post("/{task_id}/test-suites", status_code=201)
@require_permission(Permission.TASK_UPDATE)
async def create_test_suites(
    task_id: str,
    suites: list[dict],
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Batch-create test suites for a task."""
    await _load_task(session, task_id, _actor(request), role=_role(request))

    created_suites = _suites_from_items(task_id, suites)
    for suite in created_suites:
        session.add(suite)

    await session.commit()
    await _invalidate_task_caches(task_id, _actor(request))
    return {"task_id": task_id, "created": len(created_suites)}


@router.post("/{task_id}/test-suites/upload", status_code=201)
@require_permission(Permission.TASK_UPDATE)
async def upload_test_suites(
    task_id: str,
    request: Request,
    file: UploadFile = File(..., description="CSV or JSON test suite file"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Upload CSV/JSON file to batch-import test suites."""
    actor = _actor(request)
    await _load_task(session, task_id, actor, role=_role(request))

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
    await _invalidate_task_caches(task_id, actor)

    return {
        "task_id": task_id,
        "created": len(created_suites),
        "filename": file.filename,
        "message": f"Imported {len(created_suites)} test suite(s)",
    }


@router.post("/{task_id}/cancel")
@require_permission(Permission.TASK_CANCEL)
async def cancel_task(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel a running evaluation task."""
    actor = _actor(request)
    task = await _load_task(session, task_id, actor, role=_role(request))

    if not task.status.can_transition_to(TaskStatus.CANCELLED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel task in '{task.status.value}' state.",
        )

    if task.celery_task_id:
        from app.core.profiles import get_task_queue

        get_task_queue().revoke(task.celery_task_id, terminate=True)

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
    await _invalidate_task_caches(task_id, actor)

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
@require_permission(Permission.TASK_UPDATE)
async def archive_task(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Soft-archive a terminal-state task (hidden from default list)."""
    actor = _actor(request)
    task = await _load_task(session, task_id, actor, role=_role(request))

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
    await _invalidate_task_caches(task_id, actor)

    return {
        "task_id": task_id,
        "status": task.status.value,
        "is_archived": True,
        "message": "Task archived successfully",
    }


@router.post("/{task_id}/unarchive")
@require_permission(Permission.TASK_UPDATE)
async def unarchive_task(
    task_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Restore an archived task to the default list."""
    actor = _actor(request)
    task = await _load_task(session, task_id, actor, role=_role(request))

    task.is_archived = False
    await session.commit()
    await _invalidate_task_caches(task_id, actor)

    return {
        "task_id": task_id,
        "status": task.status.value,
        "is_archived": False,
        "message": "Task unarchived successfully",
    }

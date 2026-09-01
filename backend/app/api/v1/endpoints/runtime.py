# AgentFlow Intelligence v2.0 — Runtime HTTP API (legacy + Phase 7.2 service routes)
"""Legacy agent registry routes use ``app.core.runtime``; execute/query use ``app.runtime``."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.core.rbac import Permission, require_permission
from app.core.runtime.agent import Agent
from app.core.runtime.exceptions import AgentNotFoundError, DuplicateAgentError
from app.core.runtime.registry import AgentRegistry, get_agent_registry
from app.core.runtime.runtime import AgentRuntime
from app.runtime.context import RuntimeContext
from app.runtime.executor import AgentExecutor
from app.runtime.memory import InMemoryProvider
from app.runtime.service.dto import (
    ExecutionResponseDTO,
    execution_record_to_query_dto,
)
from app.runtime.service.runtime_service import RuntimeService
from app.utils.agent_config import mask_agent_config

router = APIRouter()

_DISABLED_BODY = {
    "error": "runtime_disabled",
    "message": "Agent Runtime v2 is disabled",
}

_runtime_service_instance: RuntimeService | None = None
_memory_provider_instance: InMemoryProvider | None = None


def _get_or_create_memory_provider() -> InMemoryProvider:
    """Application-scoped memory store for HTTP Runtime (enabled path only)."""
    global _memory_provider_instance
    if _memory_provider_instance is None:
        _memory_provider_instance = InMemoryProvider()
    return _memory_provider_instance


def get_runtime_service() -> RuntimeService:
    """Application-scoped ``RuntimeService`` singleton (shared ExecutionStore)."""
    global _runtime_service_instance
    if _runtime_service_instance is None:
        if getattr(settings, "ENABLE_RUNTIME_V2", False):
            memory_provider = _get_or_create_memory_provider()
            executor = AgentExecutor(memory_provider=memory_provider)
            _runtime_service_instance = RuntimeService(executor=executor)
        else:
            _runtime_service_instance = RuntimeService()
    return _runtime_service_instance


def reset_runtime_service() -> None:
    """Reset singleton — for tests only."""
    global _runtime_service_instance, _memory_provider_instance
    _runtime_service_instance = None
    _memory_provider_instance = None


def get_runtime_registry() -> AgentRegistry:
    return get_agent_registry()


def get_runtime() -> AgentRuntime:
    return AgentRuntime()


def _runtime_disabled_response() -> JSONResponse | None:
    if getattr(settings, "ENABLE_RUNTIME_V2", False):
        return None
    return JSONResponse(status_code=503, content=dict(_DISABLED_BODY))


def _public_agent(agent: Agent) -> dict[str, Any]:
    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "runner_type": agent.runner_type,
        "config": mask_agent_config(agent.config),
    }


def _build_runtime_context(agent_id: str, context: dict[str, Any]) -> RuntimeContext | None:
    if not context:
        return None
    execution_id = str(context.get("execution_id", "")).strip() or uuid.uuid4().hex
    metadata = {key: value for key, value in context.items() if key != "execution_id"}
    return RuntimeContext(
        execution_id=execution_id,
        agent_id=agent_id,
        metadata=metadata,
    )


def _execution_response_to_dict(dto: ExecutionResponseDTO) -> dict[str, Any]:
    return {
        "execution_id": dto.execution_id,
        "status": dto.status,
        "output": dto.output,
        "error": dto.error,
    }


class AgentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    runner_type: str = Field(..., min_length=1, max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)
    agent_id: str | None = Field(default=None, max_length=64)


class AgentRunRequest(BaseModel):
    input: Any = ""
    context: dict[str, Any] = Field(default_factory=dict)


class RuntimeExecuteRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=128)
    task: str = Field(..., min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


@router.post("/execute")
@require_permission(Permission.TASK_EXECUTE)
async def runtime_execute(
    request: Request,
    body: RuntimeExecuteRequest,
    service: RuntimeService = Depends(get_runtime_service),
) -> Any:
    """Execute an agent task via ``RuntimeService`` (Phase 7.2 canonical route)."""
    disabled = _runtime_disabled_response()
    if disabled is not None:
        return disabled

    runtime_context = _build_runtime_context(body.agent_id, body.context)
    dto = service.execute(
        agent_id=body.agent_id,
        task=body.task,
        context=runtime_context,
    )
    return _execution_response_to_dict(dto)


@router.get("/executions/{execution_id}")
@require_permission(Permission.TASK_READ)
async def runtime_get_execution(
    request: Request,
    execution_id: str,
    service: RuntimeService = Depends(get_runtime_service),
) -> Any:
    """Query a persisted execution by id via ``RuntimeService``."""
    disabled = _runtime_disabled_response()
    if disabled is not None:
        return disabled

    record = service.get_execution(execution_id)
    if record is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": "execution_not_found",
                "message": f"Execution not found: {execution_id}",
            },
        )

    dto = execution_record_to_query_dto(record)
    return {
        "execution_id": dto.execution_id,
        "status": dto.status,
        "output": dto.output,
        "error": dto.error,
        "created_at": dto.created_at.isoformat(),
        "updated_at": dto.updated_at.isoformat(),
    }


@router.post("/agents")
@require_permission(Permission.TASK_CREATE)
async def create_runtime_agent(
    request: Request,
    body: AgentCreateRequest,
    registry: AgentRegistry = Depends(get_runtime_registry),
) -> Any:
    disabled = _runtime_disabled_response()
    if disabled is not None:
        return disabled

    agent_id = (body.agent_id or "").strip() or uuid.uuid4().hex
    agent = Agent(
        agent_id=agent_id,
        name=body.name.strip(),
        runner_type=body.runner_type.strip().lower(),
        config=dict(body.config or {}),
    )
    try:
        registry.register(agent)
    except DuplicateAgentError:
        return JSONResponse(
            status_code=409,
            content={"error": "duplicate_agent", "message": f"Agent already registered: {agent_id}"},
        )
    return _public_agent(agent)


@router.get("/agents")
@require_permission(Permission.TASK_READ)
async def list_runtime_agents(
    request: Request,
    registry: AgentRegistry = Depends(get_runtime_registry),
) -> Any:
    disabled = _runtime_disabled_response()
    if disabled is not None:
        return disabled
    items = [_public_agent(a) for a in registry.list()]
    return {"items": items, "total": len(items)}


@router.post("/agents/{agent_id}/run")
@require_permission(Permission.TASK_EXECUTE)
async def run_runtime_agent(
    request: Request,
    agent_id: str,
    body: AgentRunRequest,
    registry: AgentRegistry = Depends(get_runtime_registry),
    runtime: AgentRuntime = Depends(get_runtime),
) -> Any:
    disabled = _runtime_disabled_response()
    if disabled is not None:
        return disabled

    try:
        agent = registry.get(agent_id)
    except AgentNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": "agent_not_found", "message": f"Agent not found: {agent_id}"},
        )

    result = await runtime.run(agent, body.input, body.context or {})
    return {
        "agent_id": result.agent_id,
        "output": result.output,
        "trace_id": result.trace_id,
    }

# (c) 2026 AgentFlow-Eval
"""Task 相关的 Pydantic 请求/响应模型。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """创建评测任务的请求体。"""

    name: str = Field(..., min_length=1, max_length=255, description="任务名称")
    description: str = Field("", description="任务描述")
    agent_config: dict[str, Any] = Field(
        default_factory=lambda: {"model": "gpt-4o", "temperature": 0},
        description="Agent 配置参数",
    )


class TaskStatusUpdate(BaseModel):
    """更新任务状态的请求体。"""

    status: str = Field(
        ...,
        pattern=r"^(created|queued|running|waiting_tool|judging|completed|failed|cancelled|timeout)$",
        description="新状态",
    )


class TaskResponse(BaseModel):
    """任务响应模型。"""

    id: str
    name: str
    description: str
    status: str
    agent_config: dict[str, Any]
    celery_task_id: str | None = None
    is_archived: bool = False
    created_by: str = "anonymous"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    test_suite_count: int = 0

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """任务列表响应。"""

    items: list[TaskResponse]
    total: int
    page: int = 1
    page_size: int = 20

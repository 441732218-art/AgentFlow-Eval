# (c) 2026 AgentFlow-Eval
"""Task 任务模型 —— 表示一次评测任务的顶层聚合根。"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PKMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.test_suite import TestSuite


class TaskStatus(str, enum.Enum):
    """任务状态枚举。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(PKMixin, TimestampMixin, Base):
    """评测任务。
    
    一个 Task 包含多个 TestSuite 测试用例，执行时逐条运行并汇总评分。
    """

    __tablename__ = "tasks"

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="任务名称",
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="任务描述",
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.PENDING,
        comment="任务状态：pending/running/completed/failed",
    )
    agent_config: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, comment="Agent 配置参数（JSON 对象）",
    )

    # ---- 关系 ----
    test_suites: Mapped[list["TestSuite"]] = relationship(
        back_populates="task", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} name={self.name!r} status={self.status.value}>"

# (c) 2026 AgentFlow-Eval
"""Task 任务模型 —— 表示一次评测任务的顶层聚合根。"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, JSON, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PKMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.test_suite import TestSuite


class TaskStatus(str, enum.Enum):
    """任务状态枚举 —— 生产级状态机。

    状态流转:
        CREATED ─► QUEUED ─► RUNNING ─► JUDGING ─► COMPLETED
                                │          │
                                ▼          ▼
                             FAILED     FAILED
                                │
                                ▼
                           CANCELLED / TIMEOUT
    """
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_TOOL = "waiting_tool"
    JUDGING = "judging"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

    # ---- 合法流转矩阵 ----
    @classmethod
    def allowed_transitions(cls) -> dict["TaskStatus", set["TaskStatus"]]:
        """返回每个状态允许流转的目标状态集合。"""
        return {
            cls.CREATED: {cls.QUEUED, cls.CANCELLED},
            cls.QUEUED: {cls.RUNNING, cls.CANCELLED, cls.TIMEOUT},
            cls.RUNNING: {cls.WAITING_TOOL, cls.JUDGING, cls.FAILED, cls.CANCELLED, cls.TIMEOUT},
            cls.WAITING_TOOL: {cls.RUNNING, cls.FAILED, cls.CANCELLED, cls.TIMEOUT},
            cls.JUDGING: {cls.COMPLETED, cls.FAILED, cls.CANCELLED},
            cls.COMPLETED: set(),
            cls.FAILED: set(),
            cls.CANCELLED: set(),
            cls.TIMEOUT: set(),
        }

    def can_transition_to(self, target: "TaskStatus") -> bool:
        """检查是否允许从当前状态流转到目标状态。"""
        return target in self.allowed_transitions().get(self, set())


class Task(PKMixin, TimestampMixin, Base):
    """评测任务。

    一个 Task 包含多个 TestSuite 测试用例，执行时逐条运行并汇总评分。
    """

    __tablename__ = "tasks"
    __table_args__ = (
        # List: WHERE created_by=? AND is_archived=0 ORDER BY created_at DESC
        Index(
            "ix_tasks_owner_archived_created",
            "created_by",
            "is_archived",
            "created_at",
        ),
        # Dashboard: WHERE status=? ORDER BY created_at DESC
        Index("ix_tasks_status_created", "status", "created_at"),
        Index("ix_tasks_created_by", "created_by"),
        Index("ix_tasks_celery_task_id", "celery_task_id"),
        Index("ix_tasks_is_archived", "is_archived"),
    )

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="任务名称",
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="任务描述",
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(
            TaskStatus,
            name="task_status",
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=TaskStatus.CREATED,
        comment="任务状态",
    )
    agent_config: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, comment="Agent 配置参数（JSON 对象）",
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None,
        comment="Celery 异步任务 ID，用于取消和状态追踪",
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="是否已归档（软归档，列表默认隐藏）",
    )
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False, default="anonymous",
        comment="创建者 actor（API Key 映射名），用于轻量多租户隔离",
    )

    # ---- 关系 ----
    test_suites: Mapped[list["TestSuite"]] = relationship(
        back_populates="task", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} name={self.name!r} status={self.status.value}>"

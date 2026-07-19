# (c) 2026 AgentFlow-Eval
"""Trace 模型 —— 记录 Agent 执行一次测试用例的完整轨迹。"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PKMixin, TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.metric_score import MetricScore
    from app.models.test_suite import TestSuite


class TraceStatus(str, enum.Enum):
    """轨迹执行状态。"""
    SUCCESS = "success"
    FAILED = "failed"


class Trace(PKMixin, TenantMixin, TimestampMixin, Base):
    """执行轨迹。

    保存 Agent 运行一次测试用例的完整 ReAct 步骤、Token 消耗和响应时间，
    是评分和链路可视化的核心数据源。
    """

    __tablename__ = "traces"
    __table_args__ = (
        # List traces for a suite ordered by time
        Index("ix_traces_suite_created", "test_suite_id", "created_at"),
        Index("ix_traces_created_at", "created_at"),
        Index("ix_traces_tenant_created", "tenant_id", "created_at"),
    )

    test_suite_id: Mapped[str] = mapped_column(
        ForeignKey("test_suites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属测试用例 ID",
    )
    user_query: Mapped[str] = mapped_column(
        Text, nullable=False, comment="本次执行使用的用户指令（快照）",
    )
    steps: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="ReAct 步骤数组，每步包含 thought/action/observation 等字段",
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="本次执行消耗的总 Token 数",
    )
    response_time_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="执行耗时（毫秒）",
    )
    status: Mapped[TraceStatus] = mapped_column(
        Enum(
            TraceStatus,
            name="trace_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=TraceStatus.SUCCESS,
        comment="执行状态：success / failed",
    )

    # ---- v1.0 新增：Token 分拆与成本追踪 ----
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="输入 Prompt Token 数",
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="输出 Completion Token 数",
    )
    cost: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="本次执行费用（USD）",
    )

    # ---- v1.0 新增：版本追踪，确保可复现 ----
    agent_version: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None,
        comment="Agent 实现版本号",
    )
    prompt_version: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None,
        comment="Prompt 模板版本号",
    )
    model_version: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None,
        comment="LLM 模型版本（如 gpt-4o-2024-05-13）",
    )
    tool_version: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None,
        comment="工具集版本号",
    )

    # ---- 关系 ----
    test_suite: Mapped["TestSuite"] = relationship(back_populates="traces")
    metric_scores: Mapped[list["MetricScore"]] = relationship(
        back_populates="trace", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Trace id={self.id} status={self.status.value} tokens={self.total_tokens}>"

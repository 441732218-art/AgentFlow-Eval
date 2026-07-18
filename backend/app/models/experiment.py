# (c) 2026 AgentFlow-Eval
"""Experiment models — multi-run comparison on the same test suites."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PKMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.task import Task


class Experiment(PKMixin, TimestampMixin, Base):
    """A comparison experiment grouping multiple evaluation runs.

    Suites are snapshotted as JSON so later base-task edits do not alter
    historical comparisons. Each run materializes a Task with cloned suites.
    """

    __tablename__ = "experiments"
    __table_args__ = (
        Index("ix_experiments_created_by", "created_by"),
        Index("ix_experiments_created_at", "created_at"),
        Index("ix_experiments_base_task_id", "base_task_id"),
        Index("ix_experiments_owner_created", "created_by", "created_at"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="实验名称")
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="实验描述"
    )
    base_task_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="可选：套件来源任务 ID",
    )
    suite_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="测试用例快照 [{user_query, expected_output, expected_tools}]",
    )
    created_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="anonymous",
        comment="创建者 actor",
    )

    runs: Mapped[list[ExperimentRun]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="ExperimentRun.created_at",
    )

    def __repr__(self) -> str:
        return f"<Experiment id={self.id} name={self.name!r}>"


class ExperimentRun(PKMixin, TimestampMixin, Base):
    """One evaluation run inside an experiment (maps 1:1 to a Task)."""

    __tablename__ = "experiment_runs"
    __table_args__ = (
        UniqueConstraint("experiment_id", "label", name="uq_experiment_run_label"),
    )

    experiment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属实验",
    )
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="对应评测任务",
    )
    label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="变体标签，如 gpt-4o / http-agent-v1",
    )
    agent_config: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="该 run 使用的 agent_config 快照",
    )

    experiment: Mapped[Experiment] = relationship(back_populates="runs")
    task: Mapped[Task] = relationship()

    def __repr__(self) -> str:
        return f"<ExperimentRun id={self.id} label={self.label!r} task={self.task_id}>"

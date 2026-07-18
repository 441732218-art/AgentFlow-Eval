# (c) 2026 AgentFlow-Eval
"""MetricScore model —— 单项评分指标记录。"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PKMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.trace import Trace


class MetricScore(PKMixin, TimestampMixin, Base):
    """评测指标得分。

    记录每个 Trace 在某个指标维度（如准确率、工具调用正确性等）的评分，
    支持 LLM 自动评分与人工审核覆盖。
    """

    __tablename__ = "metric_scores"
    __table_args__ = (
        Index("ix_metric_scores_trace_metric", "trace_id", "metric_name"),
        Index("ix_metric_scores_human_reviewed", "is_human_reviewed"),
    )

    trace_id: Mapped[str] = mapped_column(
        ForeignKey("traces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to trace",
    )
    metric_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="metric name",
    )
    score: Mapped[float] = mapped_column(
        Float, nullable=False, comment="score 0-100",
    )
    reason: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="deduction reason",
    )
    extra_metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=None, comment="extra metadata",
    )

    # ---- v1.0 新增：LLM 评分置信度 ----
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=None,
        comment="LLM 评分置信度 0.0 ~ 1.0",
    )

    # ---- v1.0 新增：人工审核覆盖 ----
    is_human_reviewed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="是否经过人工审核",
    )
    human_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=None,
        comment="人工审核给出的分数（覆盖 LLM 评分）",
    )
    reviewer: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None,
        comment="人工审核人员标识",
    )

    # ---- 关系 ----
    trace: Mapped["Trace"] = relationship(back_populates="metric_scores")

    @property
    def effective_score(self) -> float:
        """返回最终有效分数：优先使用人工审核分数。"""
        if self.is_human_reviewed and self.human_score is not None:
            return self.human_score
        return self.score

    def __repr__(self) -> str:
        return f"<MetricScore name={self.metric_name!r} score={self.score} reviewed={self.is_human_reviewed}>"

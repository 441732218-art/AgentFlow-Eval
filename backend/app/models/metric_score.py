# (c) 2026 AgentFlow-Eval
"""MetricScore model."""

from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, JSON, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, PKMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.trace import Trace


class MetricScore(PKMixin, TimestampMixin, Base):
    __tablename__ = "metric_scores"

    trace_id: Mapped[str] = mapped_column(ForeignKey("traces.id", ondelete="CASCADE"), nullable=False, comment="FK to trace")
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="metric name")
    score: Mapped[float] = mapped_column(Float, nullable=False, comment="score 0-100")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="deduction reason")
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None, comment="extra metadata")

    trace: Mapped["Trace"] = relationship(back_populates="metric_scores")

    def __repr__(self) -> str:
        return f"<MetricScore name={self.metric_name!r} score={self.score}>"

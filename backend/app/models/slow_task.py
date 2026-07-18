# (c) 2026 AgentFlow-Eval
"""Persisted slow-task samples for diagnostics across restarts."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PKMixin


class SlowTaskEvent(PKMixin, Base):
    """One slow agent/judge/pipeline sample above configured threshold."""

    __tablename__ = "slow_task_events"
    __table_args__ = (
        Index("ix_slow_task_created", "created_at"),
        Index("ix_slow_task_stage_created", "stage", "created_at"),
        Index("ix_slow_task_trace", "trace_id"),
        Index("ix_slow_task_actor", "actor"),
    )

    stage: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    duration_sec: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_sec: Mapped[float] = mapped_column(Float, nullable=False)
    ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

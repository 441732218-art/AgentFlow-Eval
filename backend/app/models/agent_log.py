# (c) 2026 AgentFlow-Eval
"""Agent observability log events (AOLS Phase 4 durable sink)."""

from sqlalchemy import Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PKMixin, TimestampMixin


class AgentLog(PKMixin, TimestampMixin, Base):
    """Structured runtime log row for query / statistics APIs.

    ``payload`` holds the full event envelope (tokens, latency, agent_context, …).
    """

    __tablename__ = "agent_logs"
    __table_args__ = (
        Index("ix_agent_logs_created_at", "created_at"),
        Index("ix_agent_logs_event_created", "event", "created_at"),
        Index("ix_agent_logs_level_created", "level", "created_at"),
        Index("ix_agent_logs_task_created", "task_id", "created_at"),
        Index("ix_agent_logs_trace_created", "trace_id", "created_at"),
        Index("ix_agent_logs_service", "service"),
    )

    level: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="info",
        comment="info|warning|error|debug",
    )
    event: Mapped[str] = mapped_column(
        String(96),
        nullable=False,
        index=True,
        comment="dot-notation event name",
    )
    service: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="agentflow-api",
        comment="emitting service",
    )
    trace_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        default=None,
        comment="correlation / request id",
    )
    task_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        default=None,
        comment="evaluation task id if any",
    )
    payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="full event fields (redacted)",
    )

    def __repr__(self) -> str:
        return f"<AgentLog {self.event} level={self.level}>"

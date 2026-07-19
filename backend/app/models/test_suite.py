# (c) 2026 AgentFlow-Eval
"""TestSuite model."""

from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, PKMixin, TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.trace import Trace


class TestSuite(PKMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "test_suites"

    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to task",
    )
    user_query: Mapped[str] = mapped_column(Text, nullable=False, comment="user instruction")
    expected_output: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="expected output")
    expected_tools: Mapped[list] = mapped_column(JSON, nullable=False, default=list, comment="expected tool names")
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None, comment="extra metadata")

    task: Mapped["Task"] = relationship(back_populates="test_suites")
    traces: Mapped[list["Trace"]] = relationship(back_populates="test_suite", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<TestSuite id={self.id}>"

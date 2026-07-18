# (c) 2026 AgentFlow-Eval
"""MediaAsset — uploaded multimodal files linked to tasks/suites."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PKMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.test_suite import TestSuite


class MediaAsset(PKMixin, TimestampMixin, Base):
    """Stored multimodal artifact with extraction results."""

    __tablename__ = "media_assets"
    __table_args__ = (
        Index("ix_media_assets_task_id", "task_id"),
        Index("ix_media_assets_suite_id", "test_suite_id"),
        Index("ix_media_assets_created_by", "created_by"),
        Index("ix_media_assets_kind", "media_kind"),
    )

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    media_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="other")

    storage_backend: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)

    extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    features: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=None)
    extract_meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=None)

    task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    test_suite_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("test_suites.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[str] = mapped_column(String(100), nullable=False, default="anonymous")

    task: Mapped[Task | None] = relationship()
    test_suite: Mapped[TestSuite | None] = relationship()

    def __repr__(self) -> str:
        return f"<MediaAsset id={self.id} kind={self.media_kind!r} file={self.filename!r}>"

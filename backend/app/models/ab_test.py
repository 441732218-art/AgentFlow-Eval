# (c) 2026 AgentFlow-Eval
"""A/B test models — online experiments with traffic split & events."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PKMixin, TenantMixin, TimestampMixin

if TYPE_CHECKING:
    pass


class ABStatus(str, enum.Enum):
    """Lifecycle of an online A/B experiment."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ABExperiment(PKMixin, TenantMixin, TimestampMixin, Base):
    """Online A/B experiment with sticky assignment and event logging.

    Complements offline ``Experiment`` (batch suite comparison):
    - AB: continuous traffic split, exposures/conversions, significance
    - Experiment: one-shot multi-config eval on fixed suites
    """

    __tablename__ = "ab_experiments"
    __table_args__ = (
        UniqueConstraint("key", name="uq_ab_experiments_key"),
        Index("ix_ab_experiments_status", "status"),
        Index("ix_ab_experiments_created_by", "created_by"),
        Index("ix_ab_experiments_tenant", "tenant_id"),
    )

    key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Stable public key used in assign API, e.g. judge_prompt_v2",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ABStatus.DRAFT.value
    )
    # Statistical config
    alpha: Mapped[float] = mapped_column(Float, nullable=False, default=0.05)
    min_sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    primary_metric: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="conversion",
        comment="conversion | score | latency_ms | custom metric name",
    )
    control_variant_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Optional link to offline Experiment
    source_experiment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False, default="anonymous"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    winner_variant_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    variants: Mapped[list[ABVariant]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="ABVariant.created_at",
    )
    assignments: Mapped[list[ABAssignment]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    events: Mapped[list[ABEvent]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )


class ABVariant(PKMixin, TimestampMixin, Base):
    """Traffic arm with payload (agent_config / feature flags)."""

    __tablename__ = "ab_variants"
    __table_args__ = (
        UniqueConstraint("experiment_id", "key", name="uq_ab_variant_key"),
        Index("ix_ab_variants_experiment_id", "experiment_id"),
    )

    experiment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ab_experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_control: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Agent / feature payload applied when unit is assigned
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    experiment: Mapped[ABExperiment] = relationship(back_populates="variants")


class ABAssignment(PKMixin, TimestampMixin, Base):
    """Sticky unit → variant mapping."""

    __tablename__ = "ab_assignments"
    __table_args__ = (
        UniqueConstraint("experiment_id", "unit_id", name="uq_ab_assignment_unit"),
        Index("ix_ab_assignments_experiment_id", "experiment_id"),
        Index("ix_ab_assignments_variant_key", "variant_key"),
    )

    experiment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ab_experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    unit_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="User/session/request unit for stickiness",
    )
    variant_key: Mapped[str] = mapped_column(String(100), nullable=False)
    bucket: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    experiment: Mapped[ABExperiment] = relationship(back_populates="assignments")


class ABEvent(PKMixin, TimestampMixin, Base):
    """Exposure / conversion / metric events for analysis."""

    __tablename__ = "ab_events"
    __table_args__ = (
        Index("ix_ab_events_experiment_id", "experiment_id"),
        Index("ix_ab_events_variant_key", "variant_key"),
        Index("ix_ab_events_event_type", "event_type"),
        Index("ix_ab_events_unit_id", "unit_id"),
        Index(
            "ix_ab_events_exp_type_created", "experiment_id", "event_type", "created_at"
        ),
    )

    experiment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ab_experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    unit_id: Mapped[str] = mapped_column(String(128), nullable=False)
    variant_key: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="exposure | conversion | metric",
    )
    metric_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    properties: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    experiment: Mapped[ABExperiment] = relationship(back_populates="events")

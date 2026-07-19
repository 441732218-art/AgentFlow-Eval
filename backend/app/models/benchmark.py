# (c) 2026 AgentFlow-Eval
"""Industry benchmark suite models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PKMixin, TenantMixin, TimestampMixin


class Benchmark(PKMixin, TenantMixin, TimestampMixin, Base):
    """Named benchmark suite (collection of cases)."""

    __tablename__ = "benchmarks"
    __table_args__ = (
        Index("ix_benchmarks_created_by", "created_by"),
        Index("ix_benchmarks_status", "status"),
        Index("ix_benchmarks_tenant_created", "tenant_id", "created_at"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active"
    )  # active|archived
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False, default="anonymous"
    )
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    cases: Mapped[list[BenchmarkCase]] = relationship(
        back_populates="benchmark",
        cascade="all, delete-orphan",
        order_by="BenchmarkCase.created_at",
    )
    runs: Mapped[list[BenchmarkRun]] = relationship(
        back_populates="benchmark",
        cascade="all, delete-orphan",
        order_by="BenchmarkRun.created_at",
    )


class BenchmarkCase(PKMixin, TenantMixin, TimestampMixin, Base):
    """Single evaluation case inside a benchmark."""

    __tablename__ = "benchmark_cases"
    __table_args__ = (
        Index("ix_benchmark_cases_benchmark", "benchmark_id"),
        Index("ix_benchmark_cases_tenant", "tenant_id"),
    )

    benchmark_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("benchmarks.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_tools: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    extra_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    benchmark: Mapped[Benchmark] = relationship(back_populates="cases")


class BenchmarkRun(PKMixin, TenantMixin, TimestampMixin, Base):
    """One execution of a benchmark against an agent configuration."""

    __tablename__ = "benchmark_runs"
    __table_args__ = (
        Index("ix_benchmark_runs_benchmark", "benchmark_id"),
        Index("ix_benchmark_runs_task", "task_id"),
        Index("ix_benchmark_runs_status", "status"),
        Index("ix_benchmark_runs_tenant", "tenant_id"),
    )

    benchmark_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("benchmarks.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    label: Mapped[str] = mapped_column(
        String(128), nullable=False, default="default"
    )  # leaderboard series key
    agent_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending|queued|running|completed|failed
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False, default="anonymous"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    benchmark: Mapped[Benchmark] = relationship(back_populates="runs")
    results: Mapped[list[BenchmarkResult]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class BenchmarkResult(PKMixin, TenantMixin, TimestampMixin, Base):
    """Per-case metrics for a benchmark run."""

    __tablename__ = "benchmark_results"
    __table_args__ = (
        Index("ix_benchmark_results_run", "run_id"),
        Index("ix_benchmark_results_case", "case_id"),
        Index("ix_benchmark_results_tenant", "tenant_id"),
    )

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("benchmark_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    case_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    run: Mapped[BenchmarkRun] = relationship(back_populates="results")

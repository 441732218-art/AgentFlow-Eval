"""Benchmark platform tables.

Revision ID: 015_benchmarks
Revises: 014_billing_limits
Create Date: 2026-07-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "015_benchmarks"
down_revision: Union[str, None] = "014_billing_limits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "benchmarks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(100), nullable=False, server_default="anonymous"),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_benchmarks_created_by", "benchmarks", ["created_by"])
    op.create_index("ix_benchmarks_status", "benchmarks", ["status"])
    op.create_index("ix_benchmarks_tenant_id", "benchmarks", ["tenant_id"])

    op.create_table(
        "benchmark_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("benchmark_id", sa.String(36), sa.ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=False, server_default=""),
        sa.Column("expected_tools", sa.JSON(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("extra_metadata", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_benchmark_cases_benchmark", "benchmark_cases", ["benchmark_id"])

    op.create_table(
        "benchmark_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("benchmark_id", sa.String(36), sa.ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(36), nullable=True),
        sa.Column("label", sa.String(128), nullable=False, server_default="default"),
        sa.Column("agent_config", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.String(100), nullable=False, server_default="anonymous"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_benchmark_runs_benchmark", "benchmark_runs", ["benchmark_id"])
    op.create_index("ix_benchmark_runs_task", "benchmark_runs", ["task_id"])

    op.create_table(
        "benchmark_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("benchmark_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=True),
        sa.Column("trace_id", sa.String(36), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("quality", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_benchmark_results_run", "benchmark_results", ["run_id"])


def downgrade() -> None:
    op.drop_table("benchmark_results")
    op.drop_table("benchmark_runs")
    op.drop_table("benchmark_cases")
    op.drop_table("benchmarks")

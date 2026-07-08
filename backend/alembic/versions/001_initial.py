"""Initial migration: create all tables with indexes.

Revision ID: 001_initial
Revises: None
Create Date: 2026-07-08
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- tasks ----
    op.create_table("tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Enum("pending","running","completed","failed", name="task_status"), nullable=False, server_default="pending"),
        sa.Column("agent_config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    # ---- test_suites ----
    op.create_table("test_suites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=False, server_default=""),
        sa.Column("expected_tools", sa.JSON(), nullable=False),
        sa.Column("extra_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_test_suites_task_id", "test_suites", ["task_id"])

    # ---- traces ----
    op.create_table("traces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("test_suite_id", sa.String(36), nullable=False),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.Enum("success","failed", name="trace_status"), nullable=False, server_default="success"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["test_suite_id"], ["test_suites.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_traces_test_suite_id", "traces", ["test_suite_id"])
    op.create_index("ix_traces_status", "traces", ["status"])

    # ---- metric_scores ----
    op.create_table("metric_scores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("extra_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["trace_id"], ["traces.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_metric_scores_trace_id", "metric_scores", ["trace_id"])
    op.create_index("ix_metric_scores_name", "metric_scores", ["metric_name"])


def downgrade() -> None:
    op.drop_table("metric_scores")
    op.drop_table("traces")
    op.drop_table("test_suites")
    op.drop_table("tasks")
    op.execute("DROP TYPE IF EXISTS task_status")
    op.execute("DROP TYPE IF EXISTS trace_status")

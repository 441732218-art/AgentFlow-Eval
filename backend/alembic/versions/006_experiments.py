"""Add experiments and experiment_runs tables for multi-variant comparison.

Revision ID: 006_experiments
Revises: 005_task_created_by
Create Date: 2026-07-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_experiments"
down_revision: Union[str, None] = "005_task_created_by"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_task_id", sa.String(length=36), nullable=True),
        sa.Column("suite_snapshot", sa.JSON(), nullable=False),
        sa.Column(
            "created_by",
            sa.String(length=100),
            nullable=False,
            server_default="anonymous",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "experiment_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("experiment_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("agent_config", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["experiment_id"], ["experiments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("experiment_id", "label", name="uq_experiment_run_label"),
    )
    op.create_index(
        "ix_experiment_runs_experiment_id",
        "experiment_runs",
        ["experiment_id"],
    )
    op.create_index(
        "ix_experiment_runs_task_id",
        "experiment_runs",
        ["task_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_experiment_runs_task_id", table_name="experiment_runs")
    op.drop_index("ix_experiment_runs_experiment_id", table_name="experiment_runs")
    op.drop_table("experiment_runs")
    op.drop_table("experiments")

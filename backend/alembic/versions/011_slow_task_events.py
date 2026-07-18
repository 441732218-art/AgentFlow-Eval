"""Slow task events table for durable diagnostics.

Revision ID: 011_slow_task_events
Revises: 010_billing
Create Date: 2026-07-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011_slow_task_events"
down_revision: Union[str, None] = "010_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "slow_task_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("duration_sec", sa.Float(), nullable=False),
        sa.Column("threshold_sec", sa.Float(), nullable=False),
        sa.Column("ref_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ok"),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("actor", sa.String(100), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_slow_task_created", "slow_task_events", ["created_at"])
    op.create_index(
        "ix_slow_task_stage_created", "slow_task_events", ["stage", "created_at"]
    )
    op.create_index("ix_slow_task_trace", "slow_task_events", ["trace_id"])
    op.create_index("ix_slow_task_actor", "slow_task_events", ["actor"])
    op.create_index("ix_slow_task_events_stage", "slow_task_events", ["stage"])


def downgrade() -> None:
    op.drop_table("slow_task_events")

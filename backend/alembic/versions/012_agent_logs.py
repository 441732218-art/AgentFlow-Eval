"""Agent logs table for AOLS durable observability.

Revision ID: 012_agent_logs
Revises: 011_slow_task_events
Create Date: 2026-07-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012_agent_logs"
down_revision: Union[str, None] = "011_slow_task_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("level", sa.String(16), nullable=False, server_default="info"),
        sa.Column("event", sa.String(96), nullable=False),
        sa.Column("service", sa.String(64), nullable=False, server_default="agentflow-api"),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("task_id", sa.String(64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_agent_logs_created_at", "agent_logs", ["created_at"])
    op.create_index("ix_agent_logs_event_created", "agent_logs", ["event", "created_at"])
    op.create_index("ix_agent_logs_level_created", "agent_logs", ["level", "created_at"])
    op.create_index("ix_agent_logs_task_created", "agent_logs", ["task_id", "created_at"])
    op.create_index("ix_agent_logs_trace_created", "agent_logs", ["trace_id", "created_at"])
    op.create_index("ix_agent_logs_service", "agent_logs", ["service"])
    op.create_index("ix_agent_logs_event", "agent_logs", ["event"])


def downgrade() -> None:
    op.drop_table("agent_logs")

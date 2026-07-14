"""Add tasks.created_by for lightweight multi-tenancy.

Revision ID: 005_task_created_by
Revises: 004_audit_logs
Create Date: 2026-07-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005_task_created_by"
down_revision: Union[str, None] = "004_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("tasks", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "created_by",
                    sa.String(100),
                    nullable=False,
                    server_default="anonymous",
                    comment="创建者 actor",
                )
            )
    else:
        op.add_column(
            "tasks",
            sa.Column(
                "created_by",
                sa.String(100),
                nullable=False,
                server_default="anonymous",
                comment="创建者 actor",
            ),
        )

    op.create_index("ix_tasks_created_by", "tasks", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_tasks_created_by", table_name="tasks")
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("tasks", schema=None) as batch_op:
            batch_op.drop_column("created_by")
    else:
        op.drop_column("tasks", "created_by")

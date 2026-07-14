"""Add tasks.is_archived soft-archive flag.

Revision ID: 003_task_is_archived
Revises: 002_v1_enterprise
Create Date: 2026-07-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_task_is_archived"
down_revision: Union[str, None] = "002_v1_enterprise"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("tasks", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "is_archived",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                    comment="是否已归档",
                )
            )
    else:
        op.add_column(
            "tasks",
            sa.Column(
                "is_archived",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
                comment="是否已归档",
            ),
        )

    op.create_index("ix_tasks_is_archived", "tasks", ["is_archived"])


def downgrade() -> None:
    op.drop_index("ix_tasks_is_archived", table_name="tasks")
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("tasks", schema=None) as batch_op:
            batch_op.drop_column("is_archived")
    else:
        op.drop_column("tasks", "is_archived")

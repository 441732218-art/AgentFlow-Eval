"""Add tenant_id and missing indexes to audit_logs.

Revision ID: 016_audit_logs_tenant
Revises: 015_benchmarks
Create Date: 2026-08-09
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "016_audit_logs_tenant"
down_revision: Union[str, None] = "015_benchmarks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('audit_logs')]
    indexes = [i['name'] for i in inspector.get_indexes('audit_logs')]

    if 'tenant_id' not in columns:
        op.add_column(
            "audit_logs",
            sa.Column("tenant_id", sa.String(length=36), nullable=True),
        )

    if 'ix_audit_logs_actor_created' not in indexes:
        op.create_index("ix_audit_logs_actor_created", "audit_logs", ["actor", "created_at"], unique=False)

    if 'ix_audit_logs_tenant_created' not in indexes:
        op.create_index("ix_audit_logs_tenant_created", "audit_logs", ["tenant_id", "created_at"], unique=False)

    if 'ix_audit_logs_tenant_id' not in indexes:
        op.create_index(op.f("ix_audit_logs_tenant_id"), "audit_logs", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_tenant_id"), table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_created", table_name="audit_logs")
    op.drop_column("audit_logs", "tenant_id")

"""Enterprise multi-tenant: tenants, members, tenant_id columns.

Revision ID: 013_enterprise_tenants
Revises: 012_agent_logs
Create Date: 2026-07-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "013_enterprise_tenants"
down_revision: Union[str, None] = "012_agent_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Core business tables that receive nullable tenant_id
_TENANT_TABLES = (
    "tasks",
    "test_suites",
    "traces",
    "metric_scores",
    "experiments",
    "experiment_runs",
    "usage_records",
    "audit_logs",
    "subscriptions",
    "invoices",
    "media_assets",
    "ab_experiments",
)


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("plan_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])
    op.create_index("ix_tenants_status", "tenants", ["status"])
    op.create_index("ix_tenants_plan_id", "tenants", ["plan_id"])

    op.create_table(
        "tenant_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="member"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_member"),
    )
    op.create_index("ix_tenant_members_tenant_id", "tenant_members", ["tenant_id"])
    op.create_index("ix_tenant_members_user", "tenant_members", ["user_id"])
    op.create_index(
        "ix_tenant_members_tenant_role", "tenant_members", ["tenant_id", "role"]
    )

    for table in _TENANT_TABLES:
        try:
            op.add_column(
                table,
                sa.Column("tenant_id", sa.String(36), nullable=True),
            )
            op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        except Exception:
            # Table may not exist on partial deploys
            pass


def downgrade() -> None:
    for table in reversed(_TENANT_TABLES):
        try:
            op.drop_index(f"ix_{table}_tenant_id", table_name=table)
            op.drop_column(table, "tenant_id")
        except Exception:
            pass
    op.drop_table("tenant_members")
    op.drop_table("tenants")

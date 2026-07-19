"""Billing plan/quota storage + plugin limits.

Revision ID: 014_billing_limits
Revises: 013_enterprise_tenants
Create Date: 2026-07-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "014_billing_limits"
down_revision: Union[str, None] = "013_enterprise_tenants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_col(table: str, column: sa.Column) -> None:
    try:
        op.add_column(table, column)
    except Exception:
        pass


def upgrade() -> None:
    _add_col(
        "billing_plans",
        sa.Column("billing_cycle", sa.String(32), nullable=False, server_default="monthly"),
    )
    _add_col(
        "billing_plans",
        sa.Column("storage_quota_mb", sa.Integer(), nullable=False, server_default="1024"),
    )
    _add_col(
        "billing_plans",
        sa.Column("plugin_quota", sa.Integer(), nullable=False, server_default="10"),
    )
    _add_col(
        "quota_balances",
        sa.Column("storage_used_mb", sa.Float(), nullable=False, server_default="0"),
    )
    _add_col(
        "quota_balances",
        sa.Column("storage_limit_mb", sa.Integer(), nullable=False, server_default="1024"),
    )
    _add_col(
        "quota_balances",
        sa.Column("plugin_used", sa.Integer(), nullable=False, server_default="0"),
    )
    _add_col(
        "quota_balances",
        sa.Column("plugin_limit", sa.Integer(), nullable=False, server_default="10"),
    )


def downgrade() -> None:
    for table, cols in (
        (
            "quota_balances",
            ("plugin_limit", "plugin_used", "storage_limit_mb", "storage_used_mb"),
        ),
        (
            "billing_plans",
            ("plugin_quota", "storage_quota_mb", "billing_cycle"),
        ),
    ):
        for c in cols:
            try:
                op.drop_column(table, c)
            except Exception:
                pass

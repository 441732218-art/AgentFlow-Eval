"""Billing tables: plans, subscriptions, usage, quotas, invoices.

Revision ID: 010_billing
Revises: 009_ab_tests
Create Date: 2026-07-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010_billing"
down_revision: Union[str, None] = "009_ab_tests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("price_month_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_quota", sa.Integer(), nullable=False, server_default="100000"),
        sa.Column("task_quota", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code", name="uq_billing_plans_code"),
    )
    op.create_index("ix_billing_plans_code", "billing_plans", ["code"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("plan_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_ref", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_subscriptions_actor", "subscriptions", ["actor"])
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])
    op.create_index(
        "ix_subscriptions_actor_status", "subscriptions", ["actor", "status"]
    )

    op.create_table(
        "usage_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("metric", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="1"),
        sa.Column("unit_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ref_type", sa.String(64), nullable=True),
        sa.Column("ref_id", sa.String(64), nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_usage_actor_created", "usage_records", ["actor", "created_at"])
    op.create_index(
        "ix_usage_metric_created", "usage_records", ["metric", "created_at"]
    )
    op.create_index("ix_usage_trace_id", "usage_records", ["trace_id"])
    op.create_index("ix_usage_records_actor", "usage_records", ["actor"])

    op.create_table(
        "quota_balances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("token_used", sa.Float(), nullable=False, server_default="0"),
        sa.Column("token_limit", sa.Integer(), nullable=False, server_default="100000"),
        sa.Column("task_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("task_limit", sa.Integer(), nullable=False, server_default="100"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("actor", "period", name="uq_quota_actor_period"),
    )
    op.create_index("ix_quota_actor_period", "quota_balances", ["actor", "period"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("line_items", sa.JSON(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_invoices_actor", "invoices", ["actor"])
    op.create_index("ix_invoices_actor_period", "invoices", ["actor", "period"])


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("quota_balances")
    op.drop_table("usage_records")
    op.drop_table("subscriptions")
    op.drop_table("billing_plans")

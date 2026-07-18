"""A/B testing tables: experiments, variants, assignments, events.

Revision ID: 009_ab_tests
Revises: 008_media_assets
Create Date: 2026-07-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009_ab_tests"
down_revision: Union[str, None] = "008_media_assets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ab_experiments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("alpha", sa.Float(), nullable=False, server_default="0.05"),
        sa.Column("min_sample_size", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("primary_metric", sa.String(64), nullable=False, server_default="conversion"),
        sa.Column("control_variant_key", sa.String(100), nullable=True),
        sa.Column("source_experiment_id", sa.String(36), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(100), nullable=False, server_default="anonymous"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("winner_variant_key", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("key", name="uq_ab_experiments_key"),
    )
    op.create_index("ix_ab_experiments_status", "ab_experiments", ["status"])
    op.create_index("ix_ab_experiments_created_by", "ab_experiments", ["created_by"])

    op.create_table(
        "ab_variants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("experiment_id", sa.String(36), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("is_control", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["experiment_id"], ["ab_experiments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("experiment_id", "key", name="uq_ab_variant_key"),
    )
    op.create_index("ix_ab_variants_experiment_id", "ab_variants", ["experiment_id"])

    op.create_table(
        "ab_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("experiment_id", sa.String(36), nullable=False),
        sa.Column("unit_id", sa.String(128), nullable=False),
        sa.Column("variant_key", sa.String(100), nullable=False),
        sa.Column("bucket", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["experiment_id"], ["ab_experiments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("experiment_id", "unit_id", name="uq_ab_assignment_unit"),
    )
    op.create_index("ix_ab_assignments_experiment_id", "ab_assignments", ["experiment_id"])
    op.create_index("ix_ab_assignments_variant_key", "ab_assignments", ["variant_key"])

    op.create_table(
        "ab_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("experiment_id", sa.String(36), nullable=False),
        sa.Column("unit_id", sa.String(128), nullable=False),
        sa.Column("variant_key", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("metric_name", sa.String(64), nullable=True),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("properties", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["experiment_id"], ["ab_experiments.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ab_events_experiment_id", "ab_events", ["experiment_id"])
    op.create_index("ix_ab_events_variant_key", "ab_events", ["variant_key"])
    op.create_index("ix_ab_events_event_type", "ab_events", ["event_type"])
    op.create_index("ix_ab_events_unit_id", "ab_events", ["unit_id"])
    op.create_index(
        "ix_ab_events_exp_type_created",
        "ab_events",
        ["experiment_id", "event_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("ab_events")
    op.drop_table("ab_assignments")
    op.drop_table("ab_variants")
    op.drop_table("ab_experiments")

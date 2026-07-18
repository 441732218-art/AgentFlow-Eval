"""Add media_assets table for multimodal uploads.

Revision ID: 008_media_assets
Revises: 007_performance_indexes
Create Date: 2026-07-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008_media_assets"
down_revision: Union[str, None] = "007_performance_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("media_kind", sa.String(length=32), nullable=False, server_default="other"),
        sa.Column("storage_backend", sa.String(length=32), nullable=False, server_default="local"),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("extract_meta", sa.JSON(), nullable=True),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("test_suite_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=False, server_default="anonymous"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["test_suite_id"], ["test_suites.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_media_assets_task_id", "media_assets", ["task_id"])
    op.create_index("ix_media_assets_suite_id", "media_assets", ["test_suite_id"])
    op.create_index("ix_media_assets_created_by", "media_assets", ["created_by"])
    op.create_index("ix_media_assets_kind", "media_assets", ["media_kind"])


def downgrade() -> None:
    op.drop_index("ix_media_assets_kind", table_name="media_assets")
    op.drop_index("ix_media_assets_created_by", table_name="media_assets")
    op.drop_index("ix_media_assets_suite_id", table_name="media_assets")
    op.drop_index("ix_media_assets_task_id", table_name="media_assets")
    op.drop_table("media_assets")

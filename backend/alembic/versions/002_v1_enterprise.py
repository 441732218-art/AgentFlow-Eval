"""v1.0 enterprise schema upgrade: expanded task status, token tracking, human review.

Revision ID: 002_v1_enterprise
Revises: 001_initial
Create Date: 2026-07-12

Changes:
- tasks: expand task_status enum, add celery_task_id column
- traces: add prompt_tokens, completion_tokens, cost, version tracking columns
- metric_scores: add confidence, is_human_reviewed, human_score, reviewer columns
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "002_v1_enterprise"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ================================================================
    # 1) tasks 表 —— 扩展状态枚举 + 新增 celery_task_id
    # ================================================================
    # 注意：SQLite 不支持 ALTER TYPE / ADD VALUE，所以使用 native_enum=False
    # 策略是将 status 列改为 VARCHAR(20)，并由应用层做校验。
    # 对于 SQLite，ALTER COLUMN 也不支持，所以用 batch mode。
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        # SQLite: 使用 batch_alter_table 重建表
        with op.batch_alter_table("tasks", schema=None) as batch_op:
            batch_op.alter_column(
                "status",
                type_=sa.String(20),
                existing_type=sa.Enum(
                    "pending", "running", "completed", "failed",
                    name="task_status",
                ),
                existing_nullable=False,
                server_default="created",
            )
            batch_op.add_column(
                sa.Column(
                    "celery_task_id", sa.String(255),
                    nullable=True,
                    comment="Celery 异步任务 ID",
                )
            )
    else:
        # PostgreSQL: 直接 ALTER TABLE
        # 先扩展 enum（Postgres 支持 ADD VALUE）
        op.execute("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'created'")
        op.execute("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'queued'")
        op.execute("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'waiting_tool'")
        op.execute("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'judging'")
        op.execute("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'cancelled'")
        op.execute("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'timeout'")

        op.add_column("tasks", sa.Column(
            "celery_task_id", sa.String(255),
            nullable=True,
            comment="Celery 异步任务 ID",
        ))

    # 为 celery_task_id 建索引，便于按 Celery ID 快速查找
    op.create_index("ix_tasks_celery_task_id", "tasks", ["celery_task_id"])

    # ================================================================
    # 2) traces 表 —— 新增 token 分拆、成本、版本列
    # ================================================================
    trace_new_columns = [
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0",
                  comment="输入 Prompt Token 数"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0",
                  comment="输出 Completion Token 数"),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0.0",
                  comment="本次执行费用（USD）"),
        sa.Column("agent_version", sa.String(100), nullable=True,
                  comment="Agent 实现版本号"),
        sa.Column("prompt_version", sa.String(100), nullable=True,
                  comment="Prompt 模板版本号"),
        sa.Column("model_version", sa.String(100), nullable=True,
                  comment="LLM 模型版本"),
        sa.Column("tool_version", sa.String(100), nullable=True,
                  comment="工具集版本号"),
    ]
    for col in trace_new_columns:
        op.add_column("traces", col)

    # ================================================================
    # 3) metric_scores 表 —— 新增置信度与人工审核字段
    # ================================================================
    metric_new_columns = [
        sa.Column("confidence", sa.Float(), nullable=True,
                  comment="LLM 评分置信度 0.0 ~ 1.0"),
        sa.Column("is_human_reviewed", sa.Boolean(), nullable=False, server_default="0",
                  comment="是否经过人工审核"),
        sa.Column("human_score", sa.Float(), nullable=True,
                  comment="人工审核分数"),
        sa.Column("reviewer", sa.String(100), nullable=True,
                  comment="人工审核人员标识"),
    ]
    for col in metric_new_columns:
        op.add_column("metric_scores", col)

    # 为人工审核过的记录建索引
    op.create_index("ix_metric_scores_reviewed", "metric_scores", ["is_human_reviewed"])


def downgrade() -> None:
    # ---- metric_scores: 移除新增列 ----
    op.drop_index("ix_metric_scores_reviewed", table_name="metric_scores")
    op.drop_column("metric_scores", "reviewer")
    op.drop_column("metric_scores", "human_score")
    op.drop_column("metric_scores", "is_human_reviewed")
    op.drop_column("metric_scores", "confidence")

    # ---- traces: 移除新增列 ----
    op.drop_column("traces", "tool_version")
    op.drop_column("traces", "model_version")
    op.drop_column("traces", "prompt_version")
    op.drop_column("traces", "agent_version")
    op.drop_column("traces", "cost")
    op.drop_column("traces", "completion_tokens")
    op.drop_column("traces", "prompt_tokens")

    # ---- tasks: 移除新增列 ----
    op.drop_index("ix_tasks_celery_task_id", table_name="tasks")
    op.drop_column("tasks", "celery_task_id")
    # 注意：SQLite 下无法缩减 enum，PostgreSQL 下也不建议 DROP VALUE
    # 降级时不回退 enum 值，因为这不影响数据完整性

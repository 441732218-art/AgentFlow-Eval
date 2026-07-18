"""Performance indexes for high-volume task / trace / score queries.

Revision ID: 007_performance_indexes
Revises: 006_experiments
Create Date: 2026-07-17

Target query patterns (Phase 3 scale):
  - Task list: filter created_by + is_archived, order by created_at DESC
  - Task by status dashboard
  - Traces by test_suite_id ordered by time
  - Metric scores by trace (+ metric_name)
  - Experiments by owner / base_task
  - Audit log by time / action
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_performance_indexes"
down_revision: Union[str, None] = "006_experiments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (index_name, table_name, columns)
_INDEXES: list[tuple[str, str, list[str]]] = [
    # ---- tasks ----
    ("ix_tasks_created_by", "tasks", ["created_by"]),
    ("ix_tasks_celery_task_id", "tasks", ["celery_task_id"]),
    ("ix_tasks_is_archived", "tasks", ["is_archived"]),
    # Hot path: list_tasks(owner, not archived) ORDER BY created_at DESC
    ("ix_tasks_owner_archived_created", "tasks", ["created_by", "is_archived", "created_at"]),
    # Dashboard / filter by status
    ("ix_tasks_status_created", "tasks", ["status", "created_at"]),
    # ---- test_suites (task_id may already exist from 001) ----
    # ---- traces ----
    ("ix_traces_suite_created", "traces", ["test_suite_id", "created_at"]),
    ("ix_traces_created_at", "traces", ["created_at"]),
    # ---- metric_scores ----
    ("ix_metric_scores_trace_metric", "metric_scores", ["trace_id", "metric_name"]),
    ("ix_metric_scores_human_reviewed", "metric_scores", ["is_human_reviewed"]),
    # ---- experiments ----
    ("ix_experiments_created_by", "experiments", ["created_by"]),
    ("ix_experiments_created_at", "experiments", ["created_at"]),
    ("ix_experiments_base_task_id", "experiments", ["base_task_id"]),
    ("ix_experiments_owner_created", "experiments", ["created_by", "created_at"]),
    # ---- audit_logs ----
    ("ix_audit_logs_created_at", "audit_logs", ["created_at"]),
    ("ix_audit_logs_action", "audit_logs", ["action"]),
    ("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"]),
    ("ix_audit_logs_actor_created", "audit_logs", ["actor", "created_at"]),
]


def _existing_indexes(bind, table: str) -> set[str]:
    inspector = sa.inspect(bind)
    try:
        return {ix["name"] for ix in inspector.get_indexes(table) if ix.get("name")}
    except Exception:
        return set()


def _table_exists(bind, table: str) -> bool:
    inspector = sa.inspect(bind)
    return table in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    for name, table, cols in _INDEXES:
        if not _table_exists(bind, table):
            continue
        existing = _existing_indexes(bind, table)
        if name in existing:
            continue
        # Skip if identical column set already covered by another index name
        op.create_index(name, table, cols, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    for name, table, _cols in reversed(_INDEXES):
        if not _table_exists(bind, table):
            continue
        existing = _existing_indexes(bind, table)
        if name not in existing:
            continue
        op.drop_index(name, table_name=table)

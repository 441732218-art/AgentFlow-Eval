"""One-off SQLite backfill for tasks.created_by."""
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///./agentflow_eval.db")
with engine.begin() as conn:
    cols = {r[1] for r in conn.execute(text("PRAGMA table_info(tasks)")).fetchall()}
    if "created_by" not in cols:
        conn.execute(
            text(
                "ALTER TABLE tasks ADD COLUMN created_by "
                "VARCHAR(100) NOT NULL DEFAULT 'anonymous'"
            )
        )
        print("added created_by")
    else:
        print("created_by already present")

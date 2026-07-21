"""Alembic 迁移环境配置。

Uses sync SQLAlchemy engines. Async URLs from app settings
(``postgresql+asyncpg://``, ``sqlite+aiosqlite://``) are rewritten for migration.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.models.base import Base

# Import all models so metadata is complete
import app.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_database_url() -> str:
    """Resolve DATABASE_URL (env wins) and convert async drivers to sync."""
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        try:
            from app.config import settings

            url = settings.DATABASE_URL
        except Exception:
            url = config.get_main_option("sqlalchemy.url") or ""
    url = (url or "").strip()
    # Alembic needs a sync driver
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    url = url.replace("postgres+asyncpg://", "postgresql+psycopg2://")
    url = url.replace("sqlite+aiosqlite://", "sqlite://")
    return url


def run_migrations_offline() -> None:
    """离线模式运行迁移（只生成 SQL 脚本，不连接数据库）。"""
    url = _sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式运行迁移（直接连接数据库执行）。"""
    url = _sync_database_url()
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

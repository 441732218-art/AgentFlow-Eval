# (c) 2026 AgentFlow-Eval
"""基础 ORM 模型类，提供 UUID 主键与时间戳字段的公共基类。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型的抽象基类。"""
    pass


class TimestampMixin:
    """混入类，自动添加 created_at / updated_at 时间戳字段。

    所有业务模型通过多重继承获得时间戳能力。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="记录创建时间",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="记录最后更新时间",
    )


class PKMixin:
    """混入类，提供 UUID 字符串主键。

    兼容 SQLite（开发）和 PostgreSQL（生产）两种后端。
    """

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="UUID 主键",
    )

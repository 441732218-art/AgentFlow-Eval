# (c) 2026 AgentFlow-Eval
"""Shared types for multimodal processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MediaKind(str, Enum):
    """High-level media category."""

    IMAGE = "image"
    PDF = "pdf"
    SPREADSHEET = "spreadsheet"
    TEXT = "text"
    OTHER = "other"


@dataclass
class ExtractResult:
    """Normalized extraction output for any media type."""

    kind: MediaKind
    text: str = ""
    features: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    pages: int | None = None
    tables: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "text": self.text,
            "features": self.features,
            "metadata": self.metadata,
            "pages": self.pages,
            "tables": self.tables,
            "warnings": self.warnings,
        }


@dataclass
class StoredObject:
    """Reference to an object in storage."""

    key: str
    backend: str
    size_bytes: int
    content_type: str
    etag: str | None = None
    url: str | None = None

# (c) 2026 AgentFlow-Eval
"""PDF text extraction (pypdf preferred, PyPDF2 fallback)."""

from __future__ import annotations

import io
import logging
from typing import Any

from app.core.multimodal.types import ExtractResult, MediaKind

logger = logging.getLogger(__name__)


def extract_pdf(data: bytes, filename: str = "document.pdf") -> ExtractResult:
    """Extract text from a PDF document page by page."""
    warnings: list[str] = []
    pages_text: list[str] = []
    metadata: dict[str, Any] = {"filename": filename}
    features: dict[str, Any] = {"byte_size": len(data)}

    reader = None
    try:
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError:
            from PyPDF2 import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(data))
    except ImportError:
        warnings.append("pypdf/PyPDF2 not installed; cannot extract PDF text")
        return ExtractResult(
            kind=MediaKind.PDF,
            text="",
            features=features,
            metadata=metadata,
            pages=0,
            warnings=warnings,
        )
    except Exception as exc:
        warnings.append(f"PDF open failed: {exc}")
        return ExtractResult(
            kind=MediaKind.PDF,
            text="",
            features=features,
            metadata=metadata,
            pages=0,
            warnings=warnings,
        )

    try:
        n = len(reader.pages)
        features["page_count"] = n
        meta = getattr(reader, "metadata", None) or {}
        if meta:
            metadata["pdf_title"] = str(
                getattr(meta, "title", None) or meta.get("/Title") or ""
            )
            metadata["pdf_author"] = str(
                getattr(meta, "author", None) or meta.get("/Author") or ""
            )

        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                warnings.append(f"page {i + 1} extract failed: {exc}")
                text = ""
            if text.strip():
                pages_text.append(f"--- page {i + 1} ---\n{text.strip()}")
    except Exception as exc:
        warnings.append(f"PDF read failed: {exc}")

    full = "\n\n".join(pages_text)
    features["char_count"] = len(full)
    features["word_count"] = len(full.split()) if full else 0

    return ExtractResult(
        kind=MediaKind.PDF,
        text=full,
        features=features,
        metadata=metadata,
        pages=features.get("page_count"),
        warnings=warnings,
    )

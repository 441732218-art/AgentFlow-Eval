# (c) 2026 AgentFlow-Eval
"""Detect media kind and dispatch to extractors."""

from __future__ import annotations

from pathlib import Path

from app.core.multimodal.extractors.image import extract_image
from app.core.multimodal.extractors.pdf import extract_pdf
from app.core.multimodal.extractors.spreadsheet import extract_spreadsheet
from app.core.multimodal.extractors.text import extract_text_file
from app.core.multimodal.types import ExtractResult, MediaKind

# 5+ formats required by acceptance criteria
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        # images
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".bmp",
        # documents
        ".pdf",
        # tables
        ".csv",
        ".tsv",
        ".xlsx",
        ".xlsm",
        # text
        ".txt",
        ".md",
        ".json",
        ".log",
    }
)

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_PDF_EXT = {".pdf"}
_SHEET_EXT = {".csv", ".tsv", ".xlsx", ".xlsm", ".xls"}
_TEXT_EXT = {".txt", ".md", ".json", ".log", ".csv", ".tsv"}  # csv also sheet


def detect_media_kind(filename: str, content_type: str | None = None) -> MediaKind:
    """Infer media kind from filename and optional MIME type."""
    ext = Path(filename).suffix.lower()
    ct = (content_type or "").lower()
    if ext in _IMAGE_EXT or ct.startswith("image/"):
        return MediaKind.IMAGE
    if ext in _PDF_EXT or ct == "application/pdf":
        return MediaKind.PDF
    if ext in {".xlsx", ".xlsm", ".xls"} or "spreadsheet" in ct or "excel" in ct:
        return MediaKind.SPREADSHEET
    if ext in {".csv", ".tsv"} or ct in {"text/csv", "text/tab-separated-values"}:
        return MediaKind.SPREADSHEET
    if ext in _TEXT_EXT or ct.startswith("text/") or ct in {"application/json"}:
        return MediaKind.TEXT
    return MediaKind.OTHER


def extract_media(
    data: bytes,
    filename: str,
    content_type: str | None = None,
) -> ExtractResult:
    """Run the appropriate extractor for the media type."""
    kind = detect_media_kind(filename, content_type)
    if kind == MediaKind.IMAGE:
        return extract_image(data, filename)
    if kind == MediaKind.PDF:
        return extract_pdf(data, filename)
    if kind == MediaKind.SPREADSHEET:
        return extract_spreadsheet(data, filename)
    if kind == MediaKind.TEXT:
        return extract_text_file(data, filename)
    # Fallback: try text decode
    result = extract_text_file(data, filename)
    result.kind = MediaKind.OTHER
    result.warnings.append("unknown media type; treated as text")
    return result

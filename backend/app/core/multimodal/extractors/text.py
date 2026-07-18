# (c) 2026 AgentFlow-Eval
"""Plain text / markdown / json extraction."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.multimodal.types import ExtractResult, MediaKind


def extract_text_file(data: bytes, filename: str = "file.txt") -> ExtractResult:
    """Decode text-like files with sensible fallbacks."""
    warnings: list[str] = []
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="replace")
        warnings.append("decoded with latin-1 fallback")

    ext = Path(filename).suffix.lower()
    metadata = {"filename": filename, "extension": ext}
    features: dict = {
        "byte_size": len(data),
        "char_count": len(text),
        "line_count": text.count("\n") + (1 if text else 0),
        "word_count": len(text.split()) if text else 0,
    }

    if ext == ".json":
        try:
            parsed = json.loads(text)
            features["json_type"] = type(parsed).__name__
            if isinstance(parsed, dict):
                features["json_keys"] = list(parsed.keys())[:50]
            text = json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError as exc:
            warnings.append(f"invalid json: {exc}")

    return ExtractResult(
        kind=MediaKind.TEXT,
        text=text,
        features=features,
        metadata=metadata,
        warnings=warnings,
    )

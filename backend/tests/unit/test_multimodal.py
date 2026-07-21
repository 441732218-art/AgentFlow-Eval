# (c) 2026 AgentFlow-Eval
"""Tests for multimodal storage, extractors, and evaluation."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.multimodal.evaluator import compare_image_features, rule_multimodal_score
from app.core.multimodal.extractors.image import cosine_similarity, extract_image
from app.core.multimodal.extractors.pdf import extract_pdf
from app.core.multimodal.extractors.spreadsheet import extract_spreadsheet
from app.core.multimodal.extractors.text import extract_text_file
from app.core.multimodal.registry import (
    SUPPORTED_EXTENSIONS,
    detect_media_kind,
    extract_media,
)
from app.core.multimodal.storage import LocalStorage
from app.core.multimodal.types import MediaKind


def _minimal_png(width: int = 8, height: int = 8) -> bytes:
    """Create a tiny valid PNG without external deps."""
    # 1x1 red pixel PNG (base64-known minimal) expanded via Pillow if present
    try:
        from PIL import Image

        buf = io.BytesIO()
        img = Image.new("RGB", (width, height), color=(200, 40, 40))
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # Hardcoded 1x1 PNG
        return bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
            "de0000000c4944415408d763f8ffff3f0005fe02fe a75b1c0000000049454e44ae426082".replace(
                " ", ""
            )
        )


class TestDetectKind:
    def test_five_plus_formats(self):
        assert len(SUPPORTED_EXTENSIONS) >= 5
        for ext in (".png", ".pdf", ".csv", ".xlsx", ".txt", ".json", ".jpg"):
            assert ext in SUPPORTED_EXTENSIONS

    def test_detect_by_extension(self):
        assert detect_media_kind("a.PNG") == MediaKind.IMAGE
        assert detect_media_kind("doc.pdf") == MediaKind.PDF
        assert detect_media_kind("t.csv") == MediaKind.SPREADSHEET
        assert detect_media_kind("x.xlsx") == MediaKind.SPREADSHEET
        assert detect_media_kind("n.md") == MediaKind.TEXT


class TestExtractors:
    def test_text_json(self):
        raw = b'{"hello": "world", "n": 1}'
        r = extract_text_file(raw, "data.json")
        assert r.kind == MediaKind.TEXT
        assert "hello" in r.text
        assert r.features.get("json_type") == "dict"

    def test_csv(self):
        raw = b"name,score\nalice,90\nbob,80\n"
        r = extract_spreadsheet(raw, "scores.csv")
        assert r.kind == MediaKind.SPREADSHEET
        assert "alice" in r.text
        assert r.tables
        assert r.tables[0]["row_count"] == 2

    def test_image_features(self):
        raw = _minimal_png(16, 12)
        r = extract_image(raw, "red.png")
        assert r.kind == MediaKind.IMAGE
        # With Pillow: width/height; without: still returns IMAGE kind
        assert r.features.get("byte_size") == len(raw)
        if "width" in r.features:
            assert r.features["width"] == 16
            assert r.features["height"] == 12
            assert "luma_hist8" in r.features

    def test_pdf_without_lib_or_with(self):
        # empty-ish invalid pdf should warn, not crash
        r = extract_pdf(b"%PDF-1.4 not a real pdf", "x.pdf")
        assert r.kind == MediaKind.PDF
        assert isinstance(r.warnings, list)

    def test_extract_media_dispatch(self):
        r = extract_media(b"hello multimodal", "note.txt", "text/plain")
        assert r.kind == MediaKind.TEXT
        assert "hello" in r.text


class TestStorage:
    @pytest.mark.asyncio
    async def test_local_put_get_delete(self, tmp_path: Path):
        store = LocalStorage(tmp_path)
        data = b"payload-bytes"
        obj = await store.put(data, filename="a.txt", content_type="text/plain")
        assert obj.backend == "local"
        assert await store.exists(obj.key)
        assert await store.get(obj.key) == data
        await store.delete(obj.key)
        assert not await store.exists(obj.key)

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self, tmp_path: Path):
        store = LocalStorage(tmp_path)
        with pytest.raises(ValueError):
            await store.get("../etc/passwd")


class TestEvaluator:
    def test_rule_score_text(self):
        from app.core.multimodal.types import ExtractResult

        ex = ExtractResult(
            kind=MediaKind.TEXT,
            text="the cat sat on the mat with scores",
            features={"word_count": 8},
        )
        s = rule_multimodal_score(ex, expected_text="cat mat", query="where is cat")
        assert 0 <= s["total"] <= 100
        assert "content_coverage" in s["scores"]
        assert s["mode"] == "rule_multimodal"

    def test_cosine(self):
        assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
        assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_compare_image_features(self):
        a = {"luma_hist8": [0.1, 0.2, 0.3, 0.4, 0, 0, 0, 0]}
        b = {"luma_hist8": [0.1, 0.2, 0.3, 0.4, 0, 0, 0, 0]}
        c = compare_image_features(a, b)
        assert c["histogram_similarity"] == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_vision_falls_back_without_key(self):
        from app.core.multimodal.evaluator import vision_llm_score
        from app.core.multimodal.types import ExtractResult

        ex = ExtractResult(
            kind=MediaKind.IMAGE, text="red square", features={"width": 10}
        )
        with patch("app.config.settings") as s:
            s.OPENAI_API_KEY = ""
            s.OPENAI_BASE_URL = ""
            s.VISION_MODEL = "gpt-4o-mini"
            # vision_llm_score imports settings inside
            result = await vision_llm_score(
                image_bytes=_minimal_png(),
                extracted=ex,
                query="what color?",
            )
        assert result["degraded"] is True
        assert result["mode"] == "rule_multimodal"

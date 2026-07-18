# (c) 2026 AgentFlow-Eval
"""Multimodal evaluation: rule metrics + optional GPT-4V / vision LLM."""

from __future__ import annotations

import base64
import logging
import mimetypes
from typing import Any

from app.core.multimodal.extractors.image import cosine_similarity
from app.core.multimodal.types import ExtractResult, MediaKind

logger = logging.getLogger(__name__)


def rule_multimodal_score(
    extracted: ExtractResult,
    *,
    expected_text: str = "",
    query: str = "",
) -> dict[str, Any]:
    """Score extraction quality without an LLM (always available).

    Dimensions (0–100 each, total average):
      - content_coverage: non-empty useful content
      - text_relevance: token overlap with expected/query
      - structure_quality: pages/tables/features present
    """
    text = (extracted.text or "").strip()
    scores: dict[str, float] = {}

    # content coverage
    if extracted.kind == MediaKind.IMAGE:
        has_feat = bool(extracted.features.get("width"))
        scores["content_coverage"] = 90.0 if has_feat else 40.0
    else:
        if len(text) > 200:
            scores["content_coverage"] = 95.0
        elif len(text) > 20:
            scores["content_coverage"] = 75.0
        elif text:
            scores["content_coverage"] = 50.0
        else:
            scores["content_coverage"] = 10.0

    # relevance via simple token overlap
    ref = (expected_text or query or "").lower()
    if ref and text:
        ref_toks = set(ref.split())
        doc_toks = set(text.lower().split())
        if ref_toks:
            recall = len(ref_toks & doc_toks) / len(ref_toks)
            scores["text_relevance"] = round(min(100.0, recall * 100), 1)
        else:
            scores["text_relevance"] = 70.0
    elif not ref:
        scores["text_relevance"] = 80.0  # no reference → neutral-good
    else:
        scores["text_relevance"] = 15.0

    # structure
    struct = 50.0
    if extracted.pages and extracted.pages > 0:
        struct += 20.0
    if extracted.tables:
        struct += 20.0
    if extracted.features:
        struct += 10.0
    scores["structure_quality"] = min(100.0, struct)

    total = round(sum(scores.values()) / len(scores), 1)
    return {
        "mode": "rule_multimodal",
        "scores": scores,
        "total": total,
        "reason": (
            f"[Rule-MM] kind={extracted.kind.value} "
            f"chars={len(text)} tables={len(extracted.tables)} "
            f"warnings={len(extracted.warnings)}"
        ),
        "kind": extracted.kind.value,
        "token_cost": 0,
        "degraded": False,
    }


async def vision_llm_score(
    *,
    image_bytes: bytes | None,
    extracted: ExtractResult,
    query: str,
    expected_text: str = "",
    model: str | None = None,
) -> dict[str, Any]:
    """Call a multimodal chat model (GPT-4V / gpt-4o style) when configured.

    Falls back to rule scoring if no API key or non-image media without text.
    """
    from app.config import settings

    api_key = settings.OPENAI_API_KEY or ""
    if not api_key:
        result = rule_multimodal_score(
            extracted, expected_text=expected_text, query=query
        )
        result["degraded"] = True
        result["reason"] += " [no OPENAI_API_KEY; rule only]"
        return result

    model_name = model or getattr(settings, "VISION_MODEL", None) or "gpt-4o-mini"
    prompt = _build_eval_prompt(query, expected_text, extracted)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.OPENAI_BASE_URL or None,
        )
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are a multimodal evaluation expert. "
                    "Score 0-100 for content_coverage, text_relevance, structure_quality. "
                    "Return ONLY JSON: "
                    '{"scores": {...}, "total": number, "reason": string}'
                ),
            }
        ]

        user_content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        if image_bytes and extracted.kind == MediaKind.IMAGE:
            mime = extracted.metadata.get("format", "png")
            mime = f"image/{str(mime).lower()}" if not str(mime).startswith("image/") else mime
            b64 = base64.b64encode(image_bytes).decode("ascii")
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                }
            )
        messages.append({"role": "user", "content": user_content})

        from app.core.resilience import default_llm_policy, protected_call_async

        policy = default_llm_policy(name=f"vision:{model_name}")

        async def _call() -> Any:
            return await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

        resp = await protected_call_async(_call, policy=policy)
        usage = resp.usage
        token_cost = (usage.prompt_tokens if usage else 0) + (
            usage.completion_tokens if usage else 0
        )
        import json

        data = json.loads(resp.choices[0].message.content or "{}")
        scores = data.get("scores") or {}
        for k in ("content_coverage", "text_relevance", "structure_quality"):
            scores.setdefault(k, 0.0)
        total = float(data.get("total") or sum(float(v) for v in scores.values()) / 3)
        return {
            "mode": "vision_llm",
            "scores": {k: float(v) for k, v in scores.items()},
            "total": round(total, 1),
            "reason": f"[Vision-LLM:{model_name}] {data.get('reason', '')}",
            "kind": extracted.kind.value,
            "token_cost": token_cost,
            "degraded": False,
            "model": model_name,
        }
    except Exception as exc:
        logger.warning("vision LLM failed: %s", exc)
        result = rule_multimodal_score(
            extracted, expected_text=expected_text, query=query
        )
        result["degraded"] = True
        result["reason"] += f" [vision failed: {exc}]"
        return result


def _build_eval_prompt(query: str, expected: str, extracted: ExtractResult) -> str:
    snippet = (extracted.text or "")[:4000]
    return (
        f"## User query\n{query or '(none)'}\n\n"
        f"## Expected\n{expected or '(none)'}\n\n"
        f"## Media kind\n{extracted.kind.value}\n\n"
        f"## Extracted text / description\n{snippet}\n\n"
        f"## Features\n{extracted.features}\n"
    )


def compare_image_features(
    a: dict[str, Any],
    b: dict[str, Any],
) -> dict[str, Any]:
    """Compare two image feature dicts (hist + optional CLIP)."""
    ha = a.get("luma_hist8") or []
    hb = b.get("luma_hist8") or []
    hist_sim = cosine_similarity(
        [float(x) for x in ha],
        [float(x) for x in hb],
    )
    clip_sim = None
    if a.get("clip_preview") and b.get("clip_preview"):
        clip_sim = cosine_similarity(
            [float(x) for x in a["clip_preview"]],
            [float(x) for x in b["clip_preview"]],
        )
    return {
        "histogram_similarity": round(hist_sim, 4),
        "clip_similarity": round(clip_sim, 4) if clip_sim is not None else None,
    }

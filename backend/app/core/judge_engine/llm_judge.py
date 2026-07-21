# (c) 2026 AgentFlow-Eval
"""LLM-as-Judge with hybrid rule-based + LLM scoring.

Architecture:
  1) Rule-based pre-scoring always runs,
  2) LLM-as-Judge refinement when API key is available,
  3) Falls back to pure rule-based when no API key / timeout / error.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from collections import OrderedDict
from typing import Any

from openai import AsyncOpenAI

from app.core.judge_engine.base import BaseJudge
from app.core.judge_engine.metrics import calc_tool_accuracy, extract_answer_text
from app.core.judge_engine.scorecard import (
    DIMENSION_WEIGHTS,
    Scorecard,
    default_scorecard,
    parse_scorecard,
)
from app.core.resilience import default_llm_policy, protected_call_async

logger = logging.getLogger(__name__)

# Re-export for callers that imported DIMENSION_WEIGHTS from this module
__all_weights__ = DIMENSION_WEIGHTS

# Fallback prompt when scorecard missing (should not happen)
SYSTEM_PROMPT = default_scorecard().to_system_prompt()

# CJK unified ideographs (rough range for Chinese/Japanese/Korean tokens)
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+")
_WORD_RE = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+")


class LLMJudge(BaseJudge):
    """Hybrid scoring engine: rule-based + optional LLM refinement.

    Features:
      - In-process LRU result cache (size configurable)
      - Optional evaluate() soft timeout
      - CJK-aware lexical answer scoring
      - Safe fallbacks when LLM refine fails
    """

    _cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
    _cache_max: int = 128

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "gpt-4o-mini",
        timeout_sec: float | None = None,
        cache_size: int | None = None,
        scorecard: Scorecard | dict[str, Any] | None = None,
    ) -> None:
        """Initialize the judge.

        Args:
            api_key: OpenAI-compatible API key; empty disables LLM refine.
            base_url: Optional custom API base URL.
            model: Chat model name for refinement.
            timeout_sec: Soft timeout for evaluate(); None reads settings.
            cache_size: LRU cache capacity; None reads settings / default 128.
            scorecard: Optional Scorecard or dict; defaults to 40/40/20 card.
        """
        api_key = (
            api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        )
        self.has_api_key = bool(api_key)
        if self.has_api_key:
            # HTTP timeout enforced by resilience layer + client-level timeout
            try:
                from app.config import settings as _s

                client_timeout = float(
                    getattr(_s, "LLM_CALL_TIMEOUT_SEC", 30.0) or 30.0
                )
            except Exception:
                client_timeout = 30.0
            self.client: AsyncOpenAI | None = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=client_timeout,
            )
        else:
            self.client = None
        self.model = model
        self.scorecard: Scorecard = (
            parse_scorecard(scorecard) if scorecard is not None else default_scorecard()
        )

        # Lazy settings import so unit tests can construct without full env
        if timeout_sec is None or cache_size is None:
            try:
                from app.config import settings as app_settings

                if timeout_sec is None:
                    timeout_sec = float(
                        getattr(app_settings, "JUDGE_TIMEOUT_SEC", 60.0) or 0
                    )
                if cache_size is None:
                    cache_size = int(
                        getattr(app_settings, "JUDGE_CACHE_SIZE", 128) or 128
                    )
            except Exception:
                timeout_sec = timeout_sec if timeout_sec is not None else 60.0
                cache_size = cache_size if cache_size is not None else 128

        self.timeout_sec = float(timeout_sec or 0)
        self.cache_size = max(0, int(cache_size or 0))
        LLMJudge._cache_max = self.cache_size or LLMJudge._cache_max

    async def evaluate(
        self,
        trace_steps: list[dict[str, Any]] | None,
        expected_output: str,
        expected_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        """Score a trace with rule-based pre-score and optional LLM refine.

        Args:
            trace_steps: ReAct step list (may be None/empty).
            expected_output: Expected final answer text.
            expected_tools: Expected tool names.

        Returns:
            Dict with scores, total, reason, token_cost, mode, details, step_analysis.
        """
        steps = list(trace_steps or [])
        tools = list(expected_tools or [])
        expected = expected_output or ""

        cache_key = self._make_cache_key(steps, expected, tools, self.scorecard)
        if self.cache_size > 0 and cache_key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
            cached = self._cache[cache_key]
            result = dict(cached)
            result["cache_hit"] = True
            return result

        if self.timeout_sec and self.timeout_sec > 0:
            try:
                result = await asyncio.wait_for(
                    self._do_evaluate(steps, expected, tools),
                    timeout=self.timeout_sec,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Judge evaluate timed out after %.1fs; falling back to rule-only",
                    self.timeout_sec,
                )
                result = self._pre_score(steps, expected, tools)
                result["mode"] = "rule_only"
                result["reason"] = (
                    result.get("reason", "") + f" [timeout after {self.timeout_sec}s]"
                )
        else:
            result = await self._do_evaluate(steps, expected, tools)

        result["cache_hit"] = False
        if self.cache_size > 0:
            self._cache_put(cache_key, result)
        return result

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the process-wide evaluation cache (useful in tests)."""
        cls._cache.clear()

    @classmethod
    def _cache_put(cls, key: str, result: dict[str, Any]) -> None:
        """Insert into LRU cache, evicting oldest entries when over capacity."""
        max_size = cls._cache_max
        if max_size <= 0:
            return
        # Store without ephemeral cache_hit flag
        stored = {k: v for k, v in result.items() if k != "cache_hit"}
        if key in cls._cache:
            cls._cache.move_to_end(key)
        cls._cache[key] = stored
        while len(cls._cache) > max_size:
            cls._cache.popitem(last=False)

    @staticmethod
    def _make_cache_key(
        trace_steps: list[dict[str, Any]],
        expected_output: str,
        expected_tools: list[str],
        scorecard: Scorecard | None = None,
    ) -> str:
        sc = scorecard or default_scorecard()
        raw = json.dumps(
            {
                "steps": trace_steps,
                "output": expected_output,
                "tools": sorted(expected_tools),
                "scorecard": sc.model_dump(),
            },
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _pre_score(
        self,
        steps: list[dict[str, Any]],
        expected_output: str,
        expected_tools: list[str],
    ) -> dict[str, Any]:
        """Rule-based pre-score using scorecard dimension weights and methods."""
        actual_tools = self._extract_tool_names(steps)
        extracted = self._extract_final_answer(steps)
        step_analysis = self._analyze_steps(steps, expected_tools)

        scores: dict[str, float] = {}
        details: dict[str, Any] = {}
        reason_parts: list[str] = []

        for dim in self.scorecard.dimensions:
            w = float(dim.weight)
            method = dim.method
            if method == "rule_tool":
                tool_pct, tool_reason = calc_tool_accuracy(actual_tools, expected_tools)
                # tool_pct is 0-100 → scale to weight points
                score = round(tool_pct / 100.0 * w, 1)
                scores[dim.key] = score
                details[dim.key] = {
                    "score": score,
                    "max": w,
                    "reason": tool_reason,
                    "expected": expected_tools,
                    "actual": actual_tools,
                }
                reason_parts.append(f"{dim.key}: {tool_reason}")
            elif method in ("lexical", "llm_or_lexical"):
                answer_score, answer_reason = self._lexical_answer_score(
                    extracted, expected_output, max_score=w
                )
                scores[dim.key] = answer_score
                details[dim.key] = {
                    "score": answer_score,
                    "max": w,
                    "reason": answer_reason,
                    "extracted_answer": extracted,
                }
                reason_parts.append(f"{dim.key}: {answer_reason}")
            else:
                # llm_only — heuristic pre-score on same 0..weight scale
                coh_score, coh_reason = self._heuristic_coherence_score(
                    steps, max_score=w
                )
                scores[dim.key] = coh_score
                details[dim.key] = {
                    "score": coh_score,
                    "max": w,
                    "reason": coh_reason,
                    "iteration_count": len(steps),
                }
                reason_parts.append(f"{dim.key}: {coh_reason}")

        pre_total = round(sum(scores.values()), 1)
        return {
            "scores": scores,
            "total": pre_total,
            "reason": "[Rule-based] " + " | ".join(reason_parts),
            "token_cost": 0,
            "details": details,
            "step_analysis": step_analysis,
            "scorecard_name": self.scorecard.name,
        }

    async def _llm_refine(
        self,
        steps: list[dict[str, Any]],
        expected_output: str,
        expected_tools: list[str],
        pre_score: dict[str, Any],
    ) -> dict[str, Any]:
        """LLM refine with retry / circuit breaker / timeout; falls back to rules."""
        if not self.client:
            result = dict(pre_score)
            result["mode"] = "rule_only"
            result["degraded"] = True
            return result

        prompt = self._build_prompt(steps, expected_output, expected_tools, pre_score)
        policy = default_llm_policy(name=f"llm_judge:{self.model}")
        system_prompt = self.scorecard.to_system_prompt()

        async def _call_llm() -> Any:
            assert self.client is not None
            return await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

        def _rule_fallback(*_a: Any, **_k: Any) -> dict[str, Any]:
            result = dict(pre_score)
            result["mode"] = "rule_only"
            result["degraded"] = True
            result["reason"] = (
                result.get("reason", "") + " [degraded: LLM unavailable, rule engine]"
            )
            return result

        try:
            response = await protected_call_async(
                _call_llm,
                policy=policy,
                fallback=None,  # parse/fallback handled below for cleaner reasons
            )
        except Exception as exc:
            logger.warning("LLM refine protected call failed: %s", exc)
            return _rule_fallback()

        usage = response.usage
        token_cost = (usage.prompt_tokens if usage else 0) + (
            usage.completion_tokens if usage else 0
        )
        try:
            data = json.loads(response.choices[0].message.content or "{}")
        except json.JSONDecodeError:
            result = dict(pre_score)
            result["token_cost"] = token_cost
            result["reason"] += " [LLM refine failed: invalid JSON]"
            result["mode"] = "rule_only"
            result["degraded"] = True
            return result

        scores = dict(data.get("scores") or {})
        for dim in self.scorecard.dimensions:
            scores.setdefault(dim.key, pre_score["scores"].get(dim.key, 0.0))
            # Clamp to [0, weight]
            try:
                scores[dim.key] = max(
                    0.0, min(float(dim.weight), float(scores[dim.key]))
                )
            except (TypeError, ValueError):
                scores[dim.key] = float(pre_score["scores"].get(dim.key, 0.0))
        result = dict(pre_score)
        result["scores"] = scores
        computed_total = round(sum(float(v) for v in scores.values()), 1)
        result["total"] = float(data.get("total", computed_total) or computed_total)
        result["reason"] = f"[LLM] {data.get('reason', pre_score['reason'])}"
        result["token_cost"] = token_cost
        result["mode"] = "hybrid"
        result["degraded"] = False
        result["scorecard_name"] = self.scorecard.name
        return result

    async def _do_evaluate(
        self,
        steps: list[dict[str, Any]],
        expected_output: str,
        expected_tools: list[str],
    ) -> dict[str, Any]:
        pre = self._pre_score(steps, expected_output, expected_tools)
        use_llm = (
            self.has_api_key
            and self.client
            and bool(getattr(self.scorecard, "llm_refine", True))
        )
        if use_llm:
            try:
                return await self._llm_refine(
                    steps, expected_output, expected_tools, pre
                )
            except Exception as exc:
                logger.warning("LLM refine failed: %s", exc)
                pre["mode"] = "rule_only"
                pre["degraded"] = True
                pre["reason"] = pre.get("reason", "") + f" [degraded: {exc}]"
                return pre
        pre["mode"] = "rule_only"
        return pre

    @staticmethod
    def _extract_tool_names(steps: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()
        for s in steps:
            n = s.get("action") or s.get("tool_name") or ""
            if n and n not in seen and n != "final_answer":
                seen.add(n)
                names.append(n)
        return names

    @staticmethod
    def _extract_final_answer(steps: list[dict[str, Any]]) -> str:
        for s in reversed(steps):
            if s.get("action") == "final_answer":
                return s.get("action_input") or s.get("observation") or ""
            if s.get("type") == "final_answer":
                return s.get("content") or s.get("observation") or ""
            if s.get("thought") and not s.get("action"):
                return s["thought"]
        return extract_answer_text(steps)

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Tokenize text for lexical scoring (English words + CJK runs).

        Args:
            text: Input string (may include mixed CJK/Latin).

        Returns:
            Lowercased token list; empty list for blank input.
        """
        if not text:
            return []
        return [t.lower() for t in _WORD_RE.findall(text)]

    @staticmethod
    def _char_bigrams(text: str) -> set[str]:
        """Character bigrams for CJK-heavy strings (fallback similarity)."""
        cleaned = re.sub(r"\s+", "", text.lower())
        if len(cleaned) < 2:
            return {cleaned} if cleaned else set()
        return {cleaned[i : i + 2] for i in range(len(cleaned) - 1)}

    @classmethod
    def _lexical_answer_score(
        cls,
        extracted: str,
        expected: str,
        *,
        max_score: float = 40.0,
    ) -> tuple[float, str]:
        """Score answer correctness via token overlap with CJK support.

        Uses word/CJK-token Jaccard-style recall against expected tokens.
        When CJK content dominates and token recall is low, falls back to
        character bigram overlap so pure Chinese answers are not zeroed.

        Args:
            max_score: Dimension weight (points); default 40 preserves legacy scale.
        """
        max_score = float(max_score) if max_score > 0 else 40.0
        if not expected:
            return max_score, "No expected output; full score."
        if not extracted:
            return 0.0, "No answer found."

        ex_tokens = set(cls.tokenize(expected))
        ac_tokens = set(cls.tokenize(extracted))
        if not ex_tokens:
            return max_score, "No words; full score."

        recall = len(ex_tokens & ac_tokens) / len(ex_tokens)

        # CJK fallback: if either side is CJK-heavy and token recall is weak
        cjk_ratio = len("".join(_CJK_RE.findall(expected))) / max(len(expected), 1)
        if cjk_ratio > 0.3 and recall < 0.5:
            bg_ex = cls._char_bigrams(expected)
            bg_ac = cls._char_bigrams(extracted)
            if bg_ex:
                bigram_recall = len(bg_ex & bg_ac) / len(bg_ex)
                recall = max(recall, bigram_recall)

        score = round(min(1.0, recall) * max_score, 1)
        if recall > 0.8:
            desc = "High"
        elif recall > 0.5:
            desc = "Moderate"
        elif recall > 0.2:
            desc = "Low"
        else:
            desc = "Minimal"
        return score, f"{desc} word overlap."

    @staticmethod
    def _heuristic_coherence_score(
        steps: list[dict[str, Any]],
        *,
        max_score: float = 20.0,
    ) -> tuple[float, str]:
        """Heuristic coherence score scaled to ``max_score`` (legacy default 20)."""
        max_score = float(max_score) if max_score > 0 else 20.0
        scale = max_score / 20.0  # deductions calibrated on 20-point scale
        if not steps:
            return max_score, "No steps; default full score."
        ded, reasons = 0.0, []
        seen: set[str] = set()
        for s in steps:
            t = (s.get("thought") or s.get("content") or "").strip().lower()
            if t and t in seen and len(t) > 5:
                ded += 4.0 * scale
                reasons.append(f"Repetition: {t[:40]}")
            elif t:
                seen.add(t)
        if len(steps) > 8:
            ded += min((len(steps) - 8) * 2, 6) * scale
            reasons.append(f"High iteration count ({len(steps)}).")
        score = round(max(0.0, max_score - ded), 1)
        reason = "; ".join(reasons) if reasons else "No issues."
        return score, reason

    @staticmethod
    def _analyze_steps(
        steps: list[dict[str, Any]],
        expected_tools: list[str],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for i, s in enumerate(steps):
            e: dict[str, Any] = {
                "index": i,
                "has_thought": bool(s.get("thought") or s.get("content")),
                "has_action": bool(s.get("action") or s.get("tool_name")),
            }
            a = s.get("action") or s.get("tool_name") or ""
            if a:
                e["action_name"] = a
                e["is_expected"] = a in expected_tools if expected_tools else None
            result.append(e)
        return result

    @staticmethod
    def _build_prompt(
        steps: list[dict[str, Any]],
        expected_output: str,
        expected_tools: list[str],
        pre_score: dict[str, Any],
    ) -> str:
        import textwrap

        steps_str = json.dumps(steps, ensure_ascii=False, indent=2, default=str)
        pre_str = json.dumps(
            {"scores": pre_score["scores"], "total": pre_score["total"]},
            ensure_ascii=False,
        )
        return textwrap.dedent(
            f"""
            ## Expected Output
            {expected_output}

            ## Expected Tools
            {json.dumps(expected_tools, ensure_ascii=False)}

            ## Agent Steps
            {steps_str}

            ## Pre-Score (for reference)
            {pre_str}

            Please output refined score as JSON.
        """
        ).strip()

    @staticmethod
    def _deep_tuple_to_list(obj: Any) -> Any:
        if isinstance(obj, tuple):
            return [LLMJudge._deep_tuple_to_list(item) for item in obj]
        if isinstance(obj, dict):
            return {k: LLMJudge._deep_tuple_to_list(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [LLMJudge._deep_tuple_to_list(item) for item in obj]
        return obj

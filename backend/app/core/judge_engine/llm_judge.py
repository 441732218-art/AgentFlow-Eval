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
from app.core.resilience import default_llm_policy, protected_call_async

logger = logging.getLogger(__name__)

DIMENSION_WEIGHTS = {
    "tool_accuracy": 40.0,
    "answer_correctness": 40.0,
    "reasoning_coherence": 20.0,
}

SYSTEM_PROMPT = """You are a rigorous AI Agent evaluation expert. Score across 3 dimensions.
1. Tool call accuracy (0-40) 2. Answer correctness (0-40) 3. Reasoning coherence (0-20)
Output ONLY valid JSON with fields: scores, total, reason."""

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
    ) -> None:
        """Initialize the judge.

        Args:
            api_key: OpenAI-compatible API key; empty disables LLM refine.
            base_url: Optional custom API base URL.
            model: Chat model name for refinement.
            timeout_sec: Soft timeout for evaluate(); None reads settings.
            cache_size: LRU cache capacity; None reads settings / default 128.
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

        cache_key = self._make_cache_key(steps, expected, tools)
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
    ) -> str:
        raw = json.dumps(
            {
                "steps": trace_steps,
                "output": expected_output,
                "tools": sorted(expected_tools),
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
        actual_tools = self._extract_tool_names(steps)
        tool_pct, tool_reason = calc_tool_accuracy(actual_tools, expected_tools)
        tool_score = round(tool_pct * 0.4, 1)
        extracted = self._extract_final_answer(steps)
        answer_score, answer_reason = self._lexical_answer_score(
            extracted, expected_output
        )
        coh_score, coh_reason = self._heuristic_coherence_score(steps)
        step_analysis = self._analyze_steps(steps, expected_tools)
        pre_total = tool_score + answer_score + coh_score
        return {
            "scores": {
                "tool_accuracy": tool_score,
                "answer_correctness": answer_score,
                "reasoning_coherence": coh_score,
            },
            "total": pre_total,
            "reason": (
                f"[Rule-based] Tool: {tool_reason} | "
                f"Answer: {answer_reason} | Coherence: {coh_reason}"
            ),
            "token_cost": 0,
            "details": {
                "tool_accuracy": {
                    "score": tool_score,
                    "reason": tool_reason,
                    "expected": expected_tools,
                    "actual": actual_tools,
                },
                "answer_correctness": {
                    "score": answer_score,
                    "reason": answer_reason,
                    "extracted_answer": extracted,
                },
                "reasoning_coherence": {
                    "score": coh_score,
                    "reason": coh_reason,
                    "iteration_count": len(steps),
                },
            },
            "step_analysis": step_analysis,
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

        async def _call_llm() -> Any:
            assert self.client is not None
            return await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
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

        scores = data.get("scores", {})
        for dim in ("tool_accuracy", "answer_correctness", "reasoning_coherence"):
            scores.setdefault(dim, pre_score["scores"].get(dim, 0.0))
        result = dict(pre_score)
        result["scores"] = scores
        result["total"] = float(data.get("total", pre_score["total"]))
        result["reason"] = f"[LLM] {data.get('reason', pre_score['reason'])}"
        result["token_cost"] = token_cost
        result["mode"] = "hybrid"
        result["degraded"] = False
        return result

    async def _do_evaluate(
        self,
        steps: list[dict[str, Any]],
        expected_output: str,
        expected_tools: list[str],
    ) -> dict[str, Any]:
        pre = self._pre_score(steps, expected_output, expected_tools)
        if self.has_api_key and self.client:
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
    ) -> tuple[float, str]:
        """Score answer correctness via token overlap with CJK support.

        Uses word/CJK-token Jaccard-style recall against expected tokens.
        When CJK content dominates and token recall is low, falls back to
        character bigram overlap so pure Chinese answers are not zeroed.
        """
        if not expected:
            return 40.0, "No expected output; full score."
        if not extracted:
            return 0.0, "No answer found."

        ex_tokens = set(cls.tokenize(expected))
        ac_tokens = set(cls.tokenize(extracted))
        if not ex_tokens:
            return 40.0, "No words; full score."

        recall = len(ex_tokens & ac_tokens) / len(ex_tokens)

        # CJK fallback: if either side is CJK-heavy and token recall is weak
        cjk_ratio = len("".join(_CJK_RE.findall(expected))) / max(len(expected), 1)
        if cjk_ratio > 0.3 and recall < 0.5:
            bg_ex = cls._char_bigrams(expected)
            bg_ac = cls._char_bigrams(extracted)
            if bg_ex:
                bigram_recall = len(bg_ex & bg_ac) / len(bg_ex)
                recall = max(recall, bigram_recall)

        score = round(min(1.0, recall) * 40.0, 1)
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
    def _heuristic_coherence_score(steps: list[dict[str, Any]]) -> tuple[float, str]:
        if not steps:
            return 20.0, "No steps; default full score."
        ded, reasons = 0.0, []
        seen: set[str] = set()
        for s in steps:
            t = (s.get("thought") or s.get("content") or "").strip().lower()
            if t and t in seen and len(t) > 5:
                ded += 4.0
                reasons.append(f"Repetition: {t[:40]}")
            elif t:
                seen.add(t)
        if len(steps) > 8:
            ded += min((len(steps) - 8) * 2, 6)
            reasons.append(f"High iteration count ({len(steps)}).")
        score = round(max(0.0, 20.0 - ded), 1)
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

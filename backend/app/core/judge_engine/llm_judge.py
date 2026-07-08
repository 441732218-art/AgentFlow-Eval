# (c) 2026 AgentFlow-Eval
"""LLM-as-Judge with hybrid rule-based + LLM scoring.
Architecture: 1) Rule-based pre-scoring always runs,
2) LLM-as-Judge refinement when API key is available.
3) Falls back to pure rule-based when no API key.
"""

import functools, hashlib, json, logging, os
from typing import Any
from openai import AsyncOpenAI
from tenacity import before_sleep_log, retry, retry_if_exception_type
from tenacity import stop_after_attempt, wait_exponential
from app.core.judge_engine.base import BaseJudge, JudgeResult
from app.core.judge_engine.metrics import calc_tool_accuracy, extract_answer_text

logger = logging.getLogger(__name__)

DIMENSION_WEIGHTS = {"tool_accuracy": 40.0, "answer_correctness": 40.0, "reasoning_coherence": 20.0}

SYSTEM_PROMPT = """You are a rigorous AI Agent evaluation expert. Score across 3 dimensions.
1. Tool call accuracy (0-40) 2. Answer correctness (0-40) 3. Reasoning coherence (0-20)
Output ONLY valid JSON with fields: scores, total, reason."""


class LLMJudge(BaseJudge):
    """Hybrid scoring engine: rule-based + optional LLM refinement."""

    def __init__(self, api_key=None, base_url=None, model="gpt-4o-mini"):
        api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.has_api_key = bool(api_key)
        if self.has_api_key:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = None
        self.model = model

    async def evaluate(self, trace_steps, expected_output, expected_tools=None):
        cache_key = self._make_cache_key(trace_steps, expected_output, expected_tools or [])
        return await self._cached_evaluate(cache_key, trace_steps, expected_output, tuple(expected_tools or []))

    @staticmethod
    def _make_cache_key(trace_steps, expected_output, expected_tools):
        raw = json.dumps({'steps': trace_steps, 'output': expected_output, 'tools': sorted(expected_tools)}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    _cache = {}

    async def _cached_evaluate(self, _cache_key, trace_steps, expected_output, expected_tools):
        if _cache_key in self._cache:
            return self._cache[_cache_key]
        result = await self._do_evaluate(trace_steps, expected_output, expected_tools or [])
        if len(LLMJudge._cache) > 128:
            LLMJudge._cache.clear()
        LLMJudge._cache[_cache_key] = result
        return result

    def _pre_score(self, steps, expected_output, expected_tools):
        actual_tools = self._extract_tool_names(steps)
        tool_pct, tool_reason = calc_tool_accuracy(actual_tools, expected_tools)
        tool_score = round(tool_pct * 0.4, 1)
        extracted = self._extract_final_answer(steps)
        answer_score, answer_reason = self._lexical_answer_score(extracted, expected_output)
        coh_score, coh_reason = self._heuristic_coherence_score(steps)
        step_analysis = self._analyze_steps(steps, expected_tools)
        pre_total = tool_score + answer_score + coh_score
        return {
            'scores': {'tool_accuracy': tool_score, 'answer_correctness': answer_score, 'reasoning_coherence': coh_score},
            'total': pre_total,
            'reason': f'[Rule-based] Tool: {tool_reason} | Answer: {answer_reason} | Coherence: {coh_reason}',
            'token_cost': 0,
            'details': {'tool_accuracy': {'score': tool_score, 'reason': tool_reason, 'expected': expected_tools, 'actual': actual_tools},
                'answer_correctness': {'score': answer_score, 'reason': answer_reason, 'extracted_answer': extracted},
                'reasoning_coherence': {'score': coh_score, 'reason': coh_reason, 'iteration_count': len(steps)}},
            'step_analysis': step_analysis,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((TimeoutError, ConnectionError)),
            before_sleep=before_sleep_log(logger, logging.WARNING), reraise=True)
    async def _llm_refine(self, steps, expected_output, expected_tools, pre_score):
        prompt = self._build_prompt(steps, expected_output, expected_tools, pre_score)
        response = await self.client.chat.completions.create(model=self.model,
            messages=[{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': prompt}],
            temperature=0.1, response_format={'type': 'json_object'})
        usage = response.usage
        token_cost = (usage.prompt_tokens if usage else 0) + (usage.completion_tokens if usage else 0)
        try:
            data = json.loads(response.choices[0].message.content or '{}')
        except json.JSONDecodeError:
            result = dict(pre_score)
            result['token_cost'] = token_cost
            result['reason'] += ' [LLM refine failed]'
            result['mode'] = 'rule_only'
            return result
        scores = data.get('scores', {})
        for dim in ('tool_accuracy', 'answer_correctness', 'reasoning_coherence'):
            scores.setdefault(dim, pre_score['scores'].get(dim, 0.0))
        result = dict(pre_score)
        result['scores'] = scores
        result['total'] = float(data.get('total', pre_score['total']))
        result['reason'] = f'[LLM] {data.get("reason", pre_score["reason"])}'
        result['token_cost'] = token_cost
        result['mode'] = 'hybrid'
        return result

    async def _do_evaluate(self, steps, expected_output, expected_tools):
        pre = self._pre_score(steps, expected_output, expected_tools)
        if self.has_api_key and self.client:
            try:
                return await self._llm_refine(steps, expected_output, expected_tools, pre)
            except Exception as exc:
                logger.warning('LLM refine failed: %s', exc)
                pre['mode'] = 'rule_only'
                return pre
        pre['mode'] = 'rule_only'
        return pre

    @staticmethod
    def _extract_tool_names(steps):
        names, seen = [], set()
        for s in steps:
            n = s.get('action') or s.get('tool_name') or ''
            if n and n not in seen and n != 'final_answer':
                seen.add(n); names.append(n)
        return names

    @staticmethod
    def _extract_final_answer(steps):
        for s in reversed(steps):
            if s.get('action') == 'final_answer':
                return s.get('action_input') or s.get('observation') or ''
            if s.get('type') == 'final_answer':
                return s.get('content') or s.get('observation') or ''
            if s.get('thought') and not s.get('action'):
                return s['thought']
        return extract_answer_text(steps)

    @staticmethod
    def _lexical_answer_score(extracted, expected):
        if not expected:
            return 40.0, 'No expected output; full score.'
        if not extracted:
            return 0.0, 'No answer found.'
        ex = set(expected.lower().split())
        ac = set(extracted.lower().split())
        if not ex:
            return 40.0, 'No words; full score.'
        r = len(ex & ac) / len(ex)
        score = round(r * 40.0, 1)
        if r > 0.8: desc = 'High'
        elif r > 0.5: desc = 'Moderate'
        elif r > 0.2: desc = 'Low'
        else: desc = 'Minimal'
        return score, f'{desc} word overlap.'

    @staticmethod
    def _heuristic_coherence_score(steps):
        if not steps:
            return 20.0, 'No steps; default full score.'
        ded, reasons = 0.0, []
        seen = set()
        for s in steps:
            t = (s.get('thought') or s.get('content') or '').strip().lower()
            if t and t in seen and len(t) > 5:
                ded += 4.0; reasons.append(f'Repetition: {t[:40]}')
            elif t:
                seen.add(t)
        if len(steps) > 8:
            ded += min((len(steps) - 8) * 2, 6)
            reasons.append(f'High iteration count ({len(steps)}).')
        score = round(max(0.0, 20.0 - ded), 1)
        reason = '; '.join(reasons) if reasons else 'No issues.'
        return score, reason

    @staticmethod
    def _analyze_steps(steps, expected_tools):
        result = []
        for i, s in enumerate(steps):
            e = {'index': i, 'has_thought': bool(s.get('thought') or s.get('content')),
                 'has_action': bool(s.get('action') or s.get('tool_name'))}
            a = s.get('action') or s.get('tool_name') or ''
            if a:
                e['action_name'] = a
                e['is_expected'] = a in expected_tools if expected_tools else None
            result.append(e)
        return result

    @staticmethod
    def _build_prompt(steps, expected_output, expected_tools, pre_score):
        import textwrap
        steps_str = json.dumps(steps, ensure_ascii=False, indent=2)
        pre_str = json.dumps({'scores': pre_score['scores'], 'total': pre_score['total']}, ensure_ascii=False)
        return textwrap.dedent(f'''
            ## Expected Output
            {expected_output}

            ## Expected Tools
            {json.dumps(expected_tools, ensure_ascii=False)}

            ## Agent Steps
            {steps_str}

            ## Pre-Score (for reference)
            {pre_str}

            Please output refined score as JSON.
        ''').strip()

    @staticmethod
    def _deep_tuple_to_list(obj):
        if isinstance(obj, tuple):
            return [LLMJudge._deep_tuple_to_list(item) for item in obj]
        if isinstance(obj, dict):
            return {k: LLMJudge._deep_tuple_to_list(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [LLMJudge._deep_tuple_to_list(item) for item in obj]
        return obj
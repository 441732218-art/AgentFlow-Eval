# (c) 2026 AgentFlow-Eval
"""Example JUDGE plugin — score based on answer length similarity."""

from __future__ import annotations

from typing import Any

from app.core.judge_engine.base import BaseJudge, JudgeResult
from app.core.plugins.base import BasePlugin, PluginContext, PluginMeta, PluginType


class LengthJudge(BaseJudge):
    """Simple deterministic judge for demos and tests."""

    async def evaluate(
        self,
        trace_steps: list[dict[str, Any]],
        expected_output: str,
        expected_tools: list[str],
    ) -> JudgeResult:
        # Extract last assistant / final answer-ish text
        answer = ""
        for step in reversed(trace_steps or []):
            if not isinstance(step, dict):
                continue
            for key in ("content", "output", "answer", "observation"):
                if step.get(key):
                    answer = str(step[key])
                    break
            if answer:
                break

        exp = (expected_output or "").strip()
        ans = answer.strip()
        if not exp and not ans:
            score = 1.0
        elif not exp or not ans:
            score = 0.0
        else:
            ratio = min(len(ans), len(exp)) / max(len(ans), len(exp))
            score = round(float(ratio), 4)

        tools_used = []
        for step in trace_steps or []:
            if isinstance(step, dict) and step.get("tool"):
                tools_used.append(str(step["tool"]))
            if isinstance(step, dict) and step.get("tool_name"):
                tools_used.append(str(step["tool_name"]))

        tool_score = 1.0
        if expected_tools:
            hit = sum(1 for t in expected_tools if t in tools_used)
            tool_score = hit / len(expected_tools)

        total = round(0.7 * score + 0.3 * tool_score, 4)
        return JudgeResult(
            scores={
                "length_similarity": score,
                "tool_coverage": tool_score,
            },
            total=total,
            reason=f"length_ratio={score}, tool_coverage={tool_score}",
            token_cost=0,
        )


class Plugin(BasePlugin):
    meta = PluginMeta(
        name="length_judge",
        version="1.0.0",
        plugin_type=PluginType.JUDGE,
        description="Rule judge: answer length ratio + tool coverage.",
        author="AgentFlow-Eval",
        provides=["length", "length_judge"],
    )

    def on_activate(self, ctx: PluginContext) -> None:
        assert ctx.register_judge is not None

        def factory() -> LengthJudge:
            return LengthJudge()

        ctx.register_judge("length", factory)
        ctx.register_judge("length_judge", factory)

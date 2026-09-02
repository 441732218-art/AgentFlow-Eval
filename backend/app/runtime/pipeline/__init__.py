# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Execution pipeline for Agent Runtime."""

from __future__ import annotations

from app.runtime.pipeline.hooks import ExecutionHook
from app.runtime.pipeline.pipeline import ExecutionPipeline

__all__ = [
    "AgentExecutionPipeline",
    "AgentExecutionResult",
    "ExecutionHook",
    "ExecutionPipeline",
    "ExecutionStep",
    "complete_step",
    "create_step",
    "fail_step",
]


def __getattr__(name: str):
    if name == "AgentExecutionPipeline":
        from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline

        return AgentExecutionPipeline
    if name == "AgentExecutionResult":
        from app.runtime.pipeline.models import AgentExecutionResult

        return AgentExecutionResult
    if name == "ExecutionStep":
        from app.runtime.pipeline.models import ExecutionStep

        return ExecutionStep
    if name == "complete_step":
        from app.runtime.pipeline.steps import complete_step

        return complete_step
    if name == "create_step":
        from app.runtime.pipeline.steps import create_step

        return create_step
    if name == "fail_step":
        from app.runtime.pipeline.steps import fail_step

        return fail_step
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

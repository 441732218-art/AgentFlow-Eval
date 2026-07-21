import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from app.core.agent_runner.base import AgentResult, BaseAgentRunner
from app.core.agent_runner.tool_sandbox import (
    BUILTIN_TOOLS,
    get_openai_tool_defs,
    run_tool_sandboxed,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    fn: Callable[..., str] | None = None

    def to_openai_tool(self) -> dict[str, Any]:
        params = self.parameters
        if params.get("type") == "object" and "properties" in params:
            schema = params
        else:
            schema = {
                "type": "object",
                "properties": params,
                **({"required": list(params.keys())} if params else {}),
            }
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }


REACT_SYSTEM_PROMPT = """You are an AI assistant that follows the ReAct pattern.

For each step:
1. **Thought**: Reason about what to do next.
2. **Action**: Choose an available tool, or write "final_answer".
3. **Action Input**: Provide parameters for the chosen action.
4. **Observation**: You will receive the result of your action.

Available tools:
"""

REACT_SINGLE_TURN_PROMPT = """Output in this format:

Thought: your reasoning
Action: tool_name or final_answer
Action Input: arguments
Final Answer: your response

Use Chinese or English as appropriate."""


@dataclass
class ReActStep:
    iteration: int
    thought: str = ""
    action: str = ""
    action_input: str = ""
    observation: str = ""
    tokens: int = 0
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "tokens": self.tokens,
        }


DEFAULT_TOOL_FUNCTIONS: dict[str, Callable[..., str]] = {
    name: meta["fn"] for name, meta in BUILTIN_TOOLS.items()
}

# Keep DEFAULT_TOOL_DEFS in sync with sandbox registry
DEFAULT_TOOL_DEFS = get_openai_tool_defs(["web_search", "calculator"])


class OpenAIReActRunner(BaseAgentRunner):
    """ReAct loop agent using OpenAI.

    Implements: Thought -> Action -> Observation -> repeat -> Final Answer.
    Supports both function-calling mode and text-parsing mode.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "gpt-4o-mini",
        max_iterations: int = 5,
    ) -> None:
        try:
            from app.config import settings as _s

            client_timeout = float(getattr(_s, "LLM_CALL_TIMEOUT_SEC", 30.0) or 30.0)
        except Exception:
            client_timeout = 30.0
        self.client = AsyncOpenAI(
            api_key=api_key, base_url=base_url, timeout=client_timeout
        )
        self.model = model
        self.max_iterations = max_iterations

    async def _chat_completion(
        self,
        messages: list[dict[str, Any]],
        openai_tools: list[dict[str, Any]] | None,
        *,
        task_id: str | None = None,
        execution_id: str | None = None,
    ) -> Any:
        """LLM chat call wrapped with retry / circuit / timeout + AOLS llm.* logs."""
        from app.core.resilience import default_llm_policy, protected_call_async

        policy = default_llm_policy(name=f"openai_react:{self.model}")
        t0 = time.monotonic()
        try:
            from app.core.observability.aols import LogEvent, emit_llm

            emit_llm(
                LogEvent.LLM_STARTED,
                provider="openai",
                model=self.model,
                temperature=0.0,
                task_id=task_id,
                execution_id=execution_id,
            )
        except Exception:
            pass

        async def _create() -> Any:
            return await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=openai_tools if openai_tools else None,
                tool_choice="auto" if openai_tools else None,
                temperature=0,
            )

        try:
            response = await protected_call_async(_create, policy=policy)
            usage = getattr(response, "usage", None)
            in_tok = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
            out_tok = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
            tot = (
                int(getattr(usage, "total_tokens", 0) or 0)
                if usage
                else (in_tok + out_tok)
            )
            try:
                from app.core.observability.aols import LogEvent, emit_llm, elapsed_ms

                emit_llm(
                    LogEvent.LLM_COMPLETED,
                    provider="openai",
                    model=self.model,
                    temperature=0.0,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    total_tokens=tot,
                    latency_ms=elapsed_ms(t0),
                    task_id=task_id,
                    execution_id=execution_id,
                )
            except Exception:
                pass
            return response
        except Exception as exc:
            try:
                from app.core.observability.aols import LogEvent, emit_llm, elapsed_ms

                emit_llm(
                    LogEvent.LLM_FAILED,
                    provider="openai",
                    model=self.model,
                    temperature=0.0,
                    latency_ms=elapsed_ms(t0),
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    task_id=task_id,
                    execution_id=execution_id,
                )
            except Exception:
                pass
            raise

    async def run(
        self,
        query: str,
        tools: list[dict[str, Any]] | None = None,
        *,
        agent_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute ReAct loop. ``agent_config`` is accepted for BaseAgentRunner parity."""
        _ = agent_config  # model/max_iterations already set on the instance
        tool_defs, tool_map = self._parse_tools(tools or DEFAULT_TOOL_DEFS)
        openai_tools = [t.to_openai_tool() for t in tool_defs]

        tool_descriptions = "\n".join(
            f"  - {t.name}: {t.description}" for t in tool_defs
        )
        system_prompt = (
            REACT_SYSTEM_PROMPT + tool_descriptions + "\n\n" + REACT_SINGLE_TURN_PROMPT
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        steps: list[ReActStep] = []
        total_tokens = 0
        final_answer: str | None = None
        status = "success"
        error_message = ""
        start_time = time.monotonic()
        execution_id = ""
        try:
            from app.core.observability.aols import (
                LogEvent,
                emit_agent,
                emit_agent_step,
                map_step_type,
                new_execution_id,
            )

            execution_id = new_execution_id()
            emit_agent(
                LogEvent.AGENT_STARTED,
                execution_id=execution_id,
                agent_id="openai_react",
                agent_version="1.0",
                model=self.model,
            )
        except Exception:
            execution_id = ""

        for iteration in range(self.max_iterations):
            step = ReActStep(iteration=iteration, timestamp=time.time())
            step_t0 = time.monotonic()

            try:
                response = await self._chat_completion(
                    messages,
                    openai_tools if tool_defs else None,
                    execution_id=execution_id or None,
                )

                choice = response.choices[0]
                msg = choice.message
                usage = response.usage
                step.tokens = usage.total_tokens if usage else 0
                total_tokens += step.tokens

                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        fn_name = tc.function.name
                        try:
                            fn_args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            fn_args = {}

                        step.action = fn_name
                        step.action_input = json.dumps(fn_args, ensure_ascii=False)
                        step.thought = msg.content or ""
                        step.observation = self._execute_tool(
                            fn_name, fn_args, tool_map
                        )

                        messages.append(
                            {
                                "role": "assistant",
                                "content": msg.content or "",
                                "tool_calls": [
                                    {
                                        "id": tc.id,
                                        "type": "function",
                                        "function": {
                                            "name": fn_name,
                                            "arguments": tc.function.arguments,
                                        },
                                    }
                                ],
                            }
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": step.observation,
                            }
                        )
                else:
                    content = msg.content or ""
                    parsed = self._parse_step(content)
                    step.thought = parsed.get("thought", content)
                    step.action = parsed.get("action", "")
                    step.action_input = parsed.get("action_input", "")

                    if (
                        step.action == "final_answer"
                        or "final answer" in content.lower()
                    ):
                        final_answer = parsed.get("action_input") or parsed.get(
                            "thought", content
                        )
                        messages.append({"role": "assistant", "content": content})
                        try:
                            from app.core.observability.aols.emit import (
                                FINAL_ANSWER,
                                elapsed_ms,
                                emit_agent_step,
                            )

                            emit_agent_step(
                                step_index=iteration,
                                step_type=FINAL_ANSWER,
                                execution_id=execution_id or None,
                                tokens=step.tokens,
                                latency_ms=elapsed_ms(step_t0),
                                success=True,
                            )
                        except Exception:
                            pass
                        steps.append(step)
                        break

                    if step.action and step.action != "final_answer":
                        step.observation = self._execute_tool(
                            step.action,
                            self._parse_action_input(step.action_input),
                            tool_map,
                        )
                        messages.append({"role": "assistant", "content": content})
                        messages.append(
                            {
                                "role": "user",
                                "content": f"Observation: {step.observation}",
                            }
                        )
                    else:
                        final_answer = content
                        messages.append({"role": "assistant", "content": content})
                        steps.append(step)
                        break

            except Exception as exc:
                logger.exception("ReAct iteration %d failed: %s", iteration, exc)
                step.observation = f"[Error: {exc}]"
                if iteration == 0:
                    status = "failed"
                    error_message = str(exc)

            # Step-level structured log
            try:
                from app.core.observability.aols.emit import (
                    elapsed_ms,
                    emit_agent_step,
                    map_step_type,
                )

                st = map_step_type(
                    thought=step.thought,
                    action=step.action,
                    observation=step.observation,
                    is_final=bool(
                        step.action
                        and step.action.lower() in {"final_answer", "final answer"}
                    ),
                    has_tool=bool(
                        step.action and step.action.lower() not in {"", "final_answer"}
                    ),
                )
                emit_agent_step(
                    step_index=iteration,
                    step_type=st,
                    execution_id=execution_id or None,
                    tokens=step.tokens,
                    tool_name=step.action or None,
                    latency_ms=elapsed_ms(step_t0),
                    success="[Error:" not in (step.observation or ""),
                )
            except Exception:
                pass

            steps.append(step)

        if final_answer is None and steps:
            last_step = steps[-1]
            final_answer = last_step.thought or last_step.observation or "[No answer]"
            if status == "success":
                status = "max_iterations_reached"

        elapsed_ms_total = int((time.monotonic() - start_time) * 1000)
        step_dicts = [s.to_dict() for s in steps]

        try:
            from app.core.observability.aols import (
                LogEvent,
                detect_and_emit_loop,
                emit_agent,
            )

            detect_and_emit_loop(step_dicts, execution_id=execution_id or None)
            if status == "failed":
                emit_agent(
                    LogEvent.AGENT_FAILED,
                    execution_id=execution_id or None,
                    agent_id="openai_react",
                    agent_version="1.0",
                    model=self.model,
                    duration_ms=elapsed_ms_total,
                    total_tokens=total_tokens,
                    status=status,
                    error_message=error_message,
                    iterations=len(steps),
                )
            else:
                emit_agent(
                    LogEvent.AGENT_COMPLETED,
                    execution_id=execution_id or None,
                    agent_id="openai_react",
                    agent_version="1.0",
                    model=self.model,
                    duration_ms=elapsed_ms_total,
                    total_tokens=total_tokens,
                    status=status,
                    iterations=len(steps),
                )
        except Exception:
            pass

        return {
            "steps": step_dicts,
            "total_tokens": total_tokens,
            "iterations": len(steps),
            "final_answer": final_answer,
            "status": status,
            "error_message": error_message,
            "response_time_ms": elapsed_ms_total,
            "execution_id": execution_id,
            "model": self.model,
        }

    def _parse_tools(self, raw_tools=None):
        if raw_tools is None:
            return [], {}
        defs: list[ToolDefinition] = []
        for t in raw_tools:
            if isinstance(t, ToolDefinition):
                defs.append(t)
            elif isinstance(t, dict):
                fn_info = t.get("function", t)
                if isinstance(fn_info, dict):
                    defs.append(
                        ToolDefinition(
                            name=fn_info.get("name", t.get("name", "unknown")),
                            description=fn_info.get(
                                "description", t.get("description", "")
                            ),
                            parameters=fn_info.get("parameters", {}).get(
                                "properties", fn_info.get("parameters", {})
                            ),
                            fn=t.get("fn") or fn_info.get("fn"),
                        )
                    )
        return defs, {d.name: d for d in defs}

    def _execute_tool(
        self, name: str, args: dict[str, Any], tool_map: dict[str, ToolDefinition]
    ) -> str:
        """Execute tools via sandbox (timeout + truncation + allowlist)."""
        tool = tool_map.get(name)
        custom_fn = tool.fn if tool and tool.fn else DEFAULT_TOOL_FUNCTIONS.get(name)
        return run_tool_sandboxed(name, args or {}, custom_fn=custom_fn)

    @staticmethod
    def _parse_step(text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        lines = text.strip().split("\n")
        prefixes = [
            ("Thought:", "thought"),
            ("Thought：", "thought"),
            ("Action:", "action"),
            ("Action：", "action"),
            ("Action Input:", "action_input"),
            ("Action Input：", "action_input"),
            ("Observation:", "observation"),
            ("Observation：", "observation"),
            ("Final Answer:", "final_answer"),
            ("Final Answer：", "final_answer"),
        ]
        for line in lines:
            s = line.strip()
            for prefix, key in prefixes:
                if s.lower().startswith(prefix.lower()):
                    value = s[len(prefix) :].strip()
                    if value:
                        result[key] = value
        return result

    @staticmethod
    def _parse_action_input(raw: str) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
        if "=" in raw:
            result = {}
            for part in raw.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    result[k.strip()] = v.strip().strip("\"'")
            if result:
                return result
        return {"input": raw}


class OpenAIRunner(BaseAgentRunner):
    """Legacy single-turn executor. Retained for backward compatibility."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def run(
        self,
        query: str,
        tools: list[Any] | None = None,
        *,
        agent_config: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Legacy single-turn run — unified BaseAgentRunner signature."""
        _ = tools
        cfg = dict(agent_config or {})
        model = cfg.get("model", "gpt-4o")
        temperature = cfg.get("temperature", 0)
        max_tokens = cfg.get("max_tokens", 4096)
        start_time = time.monotonic()
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": REACT_SYSTEM_PROMPT
                        + "\n"
                        + REACT_SINGLE_TURN_PROMPT,
                    },
                    {"role": "user", "content": query},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            content = response.choices[0].message.content or ""
            total_tokens = response.usage.total_tokens if response.usage else 0
            steps = self._parse_react_steps(content)
            return AgentResult(
                steps=steps,
                total_tokens=total_tokens,
                response_time_ms=elapsed_ms,
                status="success",
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.exception("Agent execution failed: %s", exc)
            return AgentResult(
                steps=[{"role": "error", "content": str(exc)}],
                total_tokens=0,
                response_time_ms=elapsed_ms,
                status="failed",
                error_message=str(exc),
            )

    @staticmethod
    def _parse_react_steps(content: str) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        lines = content.split("\n")
        current_step: dict[str, Any] = {}
        step_role: str | None = None
        prefixes = [
            ("Thought:", "thought"),
            ("Thought：", "thought"),
            ("Action:", "action"),
            ("Action：", "action"),
            ("Action Input:", "action_input"),
            ("Action Input：", "action_input"),
            ("Observation:", "observation"),
            ("Observation：", "observation"),
            ("Final Answer:", "final_answer"),
            ("Final Answer：", "final_answer"),
        ]
        for line in lines:
            s = line.strip()
            matched = False
            for prefix, ptype in prefixes:
                if s.lower().startswith(prefix.lower()):
                    if current_step and step_role:
                        current_step["content"] = current_step.get(
                            "content", ""
                        ).strip()
                        steps.append(current_step)
                    current_step = {
                        "role": "tool" if ptype == "observation" else "assistant",
                        "type": ptype,
                    }
                    step_role = ptype
                    value = s[len(prefix) :].strip()
                    if ptype in ("thought", "final_answer", "observation"):
                        current_step["content"] = value
                    elif ptype == "action":
                        current_step["tool_name"] = value
                    elif ptype == "action_input":
                        current_step["tool_input"] = value
                    matched = True
                    break
            if not matched and current_step and s:
                prev = current_step.get("content", "")
                current_step["content"] = (prev + "\n" + s).strip()
        if current_step and step_role:
            current_step["content"] = current_step.get("content", "").strip()
            steps.append(current_step)
        if not steps:
            steps.append(
                {
                    "role": "assistant",
                    "type": "final_answer",
                    "content": content.strip(),
                }
            )
        return steps

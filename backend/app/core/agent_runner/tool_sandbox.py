# (c) 2026 AgentFlow-Eval
"""Safe built-in tool registry and sandboxed execution."""

from __future__ import annotations

import ast
import json
import logging
import operator as op
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Global executor for tool timeouts (Windows-friendly vs signals)
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tool-sandbox")

DEFAULT_TOOL_TIMEOUT_SEC = 3.0
MAX_OUTPUT_CHARS = 4000


class ToolSandboxError(Exception):
    """Raised when tool execution is rejected or fails safely."""


# ---------------------------------------------------------------------------
# Safe built-in implementations (no network, no filesystem, no eval)
# ---------------------------------------------------------------------------


def tool_calculator(expression: str = "", **kwargs: Any) -> str:
    """Evaluate a restricted arithmetic expression."""
    expr = (expression or kwargs.get("expr") or "").strip()
    if not expr:
        return "Error: empty expression"
    if len(expr) > 200:
        return "Error: expression too long"

    allowed_ops = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.Pow: op.pow,
        ast.USub: op.neg,
        ast.UAdd: op.pos,
        ast.Mod: op.mod,
    }

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return float(node.value)
            raise ValueError(f"Unsupported constant: {node.value!r}")
        if isinstance(node, ast.BinOp):
            fn = allowed_ops.get(type(node.op))
            if not fn:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return fn(_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            fn = allowed_ops.get(type(node.op))
            if not fn:
                raise ValueError(f"Unsupported unary: {type(node.op).__name__}")
            return fn(_eval(node.operand))
        raise ValueError(f"Unsupported syntax: {type(node).__name__}")

    try:
        tree = ast.parse(expr, mode="eval")
        # Reject names/calls/attributes entirely
        for n in ast.walk(tree):
            if isinstance(n, (ast.Name, ast.Call, ast.Attribute, ast.Subscript)):
                raise ValueError("Only numeric expressions are allowed")
        result = _eval(tree)
        return f"Result: {result}"
    except Exception as exc:
        return f"Error: {exc}"


def tool_web_search(query: str = "", **kwargs: Any) -> str:
    """Deterministic simulated search (no external network)."""
    q = (query or kwargs.get("q") or "").strip()
    if not q:
        return "Error: empty query"
    return (
        f"[Sandbox web_search] query={q!r}\n"
        f"Top result: Simulated document about '{q[:80]}'. "
        f"Note: network is disabled in the evaluation sandbox."
    )


def tool_current_datetime(timezone_name: str = "UTC", **kwargs: Any) -> str:
    """Return current UTC time (sandbox-safe)."""
    _ = timezone_name or kwargs.get("tz")
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def tool_json_get(data: str = "", path: str = "", **kwargs: Any) -> str:
    """Get a dotted path from a JSON string, e.g. path='user.name'."""
    raw = data or kwargs.get("json") or "{}"
    path = path or kwargs.get("key") or ""
    try:
        obj = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as exc:
        return f"Error: invalid JSON ({exc})"
    if not path:
        return json.dumps(obj, ensure_ascii=False)[:MAX_OUTPUT_CHARS]
    cur: Any = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return f"Error: path not found: {path}"
    if isinstance(cur, (dict, list)):
        return json.dumps(cur, ensure_ascii=False)[:MAX_OUTPUT_CHARS]
    return str(cur)[:MAX_OUTPUT_CHARS]


def tool_regex_extract(text: str = "", pattern: str = "", **kwargs: Any) -> str:
    """Extract first regex match (timeout-bound, no catastrophic patterns enforced lightly)."""
    text = text or kwargs.get("input") or ""
    pattern = pattern or kwargs.get("regex") or ""
    if not pattern:
        return "Error: empty pattern"
    if len(pattern) > 200 or len(text) > 50_000:
        return "Error: input too large"
    try:
        m = re.search(pattern, text, flags=re.MULTILINE)
        if not m:
            return "No match"
        return m.group(0)[:MAX_OUTPUT_CHARS]
    except re.error as exc:
        return f"Error: invalid regex ({exc})"


BUILTIN_TOOLS: dict[str, dict[str, Any]] = {
    "calculator": {
        "description": "Perform safe arithmetic calculations.",
        "parameters": {
            "expression": {"type": "string", "description": "Math expression, e.g. (1+2)*3"},
        },
        "required": ["expression"],
        "fn": tool_calculator,
    },
    "web_search": {
        "description": "Search the web for information (sandbox simulation, no network).",
        "parameters": {
            "query": {"type": "string", "description": "The search query"},
        },
        "required": ["query"],
        "fn": tool_web_search,
    },
    "current_datetime": {
        "description": "Get the current UTC datetime in ISO format.",
        "parameters": {
            "timezone_name": {"type": "string", "description": "Ignored; always UTC in sandbox"},
        },
        "required": [],
        "fn": tool_current_datetime,
    },
    "json_get": {
        "description": "Parse JSON and return a dotted path value.",
        "parameters": {
            "data": {"type": "string", "description": "JSON string"},
            "path": {"type": "string", "description": "Dotted path, e.g. user.name"},
        },
        "required": ["data"],
        "fn": tool_json_get,
    },
    "regex_extract": {
        "description": "Extract the first regex match from text.",
        "parameters": {
            "text": {"type": "string", "description": "Input text"},
            "pattern": {"type": "string", "description": "Regular expression"},
        },
        "required": ["text", "pattern"],
        "fn": tool_regex_extract,
    },
}


def get_openai_tool_defs(names: list[str] | None = None) -> list[dict[str, Any]]:
    """Return OpenAI-format tool definitions for the given names (or all)."""
    selected = names or list(BUILTIN_TOOLS.keys())
    out: list[dict[str, Any]] = []
    for name in selected:
        meta = BUILTIN_TOOLS.get(name)
        if not meta:
            # Unknown expected tool: still expose a stub definition for the model
            out.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": f"Tool: {name}",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            })
            continue
        out.append({
            "type": "function",
            "function": {
                "name": name,
                "description": meta["description"],
                "parameters": {
                    "type": "object",
                    "properties": meta["parameters"],
                    "required": meta.get("required") or [],
                },
            },
        })
    return out


def get_tool_function(name: str) -> Callable[..., str] | None:
    meta = BUILTIN_TOOLS.get(name)
    return meta["fn"] if meta else None


def run_tool_sandboxed(
    name: str,
    args: dict[str, Any] | None = None,
    *,
    timeout_sec: float = DEFAULT_TOOL_TIMEOUT_SEC,
    custom_fn: Callable[..., str] | None = None,
) -> str:
    """Execute a tool with timeout and output truncation.

    Unknown tools without custom_fn return a sandbox denial message
    (never executes arbitrary code).
    """
    args = args or {}
    fn = custom_fn or get_tool_function(name)
    if fn is None:
        return (
            f"[Sandbox] Tool '{name}' is not registered. "
            f"Available: {', '.join(sorted(BUILTIN_TOOLS))}."
        )

    def _call() -> str:
        try:
            # Prefer kwargs; fall back to single positional if needed
            return str(fn(**args))
        except TypeError:
            # Map common single-arg tools
            if len(args) == 1:
                return str(fn(next(iter(args.values()))))
            raise

    try:
        future = _EXECUTOR.submit(_call)
        result = future.result(timeout=timeout_sec)
    except FuturesTimeout:
        return f"[Sandbox] Tool '{name}' timed out after {timeout_sec}s"
    except Exception as exc:
        logger.warning("Tool %s failed: %s", name, exc)
        return f"[Sandbox] Tool '{name}' error: {exc}"

    text = str(result)
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + "…[truncated]"
    return text


def resolve_tools_for_suite(expected_tools: list[str] | None) -> list[dict[str, Any]]:
    """Build tool defs for a test suite: expected tools + always-safe defaults."""
    names = list(expected_tools or [])
    # Always include calculator & web_search as common defaults when empty
    if not names:
        names = ["web_search", "calculator"]
    # Deduplicate preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for n in names:
        if n and n not in seen:
            seen.add(n)
            ordered.append(n)
    defs = get_openai_tool_defs(ordered)
    # Attach sandbox fn handles for runner map
    for d in defs:
        name = d["function"]["name"]
        d["fn"] = get_tool_function(name)
    return defs

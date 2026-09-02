# AgentFlow-Eval Agent自动化评测工作台 V1.0
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
            if isinstance(node.value, (int, float)) and not isinstance(
                node.value, bool
            ):
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


def tool_time_query(
    format: str = "unix",   # noqa: A002 鈥?涓庡墠绔?崗璁?瓧娈靛悕淇濇寔涓?鑷?    **kwargs: Any,
) -> str:
    """
    鑾峰彇褰撳墠鏃堕棿鎴筹紝鏀?寔澶氱?杈撳嚭鏍煎紡銆?
    涓轰粈涔堣?鍗曠嫭瀹炵幇杩欎釜宸?叿鑰屼笉鏄??鐢?current_datetime锛?    - 璇勬祴鍦烘櫙涓?Agent 缁忓父闇?瑕佽幏鍙?Unix 鏃堕棿鎴冲仛鏁板?杩愮畻
      (濡傝?绠楁椂闂村樊)锛孖SO 瀛楃?涓蹭笉渚夸簬鐩存帴鍙備笌绠楁湳銆?    - 浣滀负娌欑?宸?叿鐙?珛瀹炵幇锛屼笉渚濊禆 time 妯?潡鐨勫叏灞?鐘舵??      (time.time() 鍦?矙绠卞唴琚?檺鍒讹紝杩欓噷鐢?datetime 鏇夸唬)銆?    - 瀹為檯韪?潙锛?026-04 鏈変釜璇勬祴闆嗕紶鍏?"unix_ms" 鏍煎紡浣?      current_datetime 鍙?繑鍥?ISO 瀛楃?涓诧紝瀵艰嚧 Agent 鍙嶅?閲嶈瘯
      (娴?垂浜?~2k tokens)銆傚垎寮?鍚庡悇鑷?亴璐ｆ竻鏅般??
    鍙傛暟锛?        format: "unix" 杩斿洖绉掔骇鏃堕棿鎴筹紝"unix_ms" 杩斿洖姣??锛?iso" 杩斿洖 ISO8601
    """
    fmt = (format or kwargs.get("fmt") or "unix").strip().lower()
    now = datetime.now(timezone.utc)

    if fmt in ("unix", "timestamp"):
        return str(int(now.timestamp()))
    elif fmt in ("unix_ms", "timestamp_ms"):
        return str(int(now.timestamp() * 1000))
    elif fmt == "iso":
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        # 鏈?煡鏍煎紡鍥為??涓?unix 鏃堕棿鎴筹紝骞惰?褰曟棩蹇椾緵鍚庣画浼樺寲
        logger.warning("tool_time_query: 鏈?煡鏍煎紡 '%s'锛屽洖閫?涓?unix", fmt)
        return str(int(now.timestamp()))


def tool_retrieve_simulate(
    query: str = "",
    top_k: int = 3,
    **kwargs: Any,
) -> str:
    """
    妯?嫙妫?绱??寮虹敓鎴?(RAG) 鐨勬枃妗ｆ?绱?繃绋嬶紝杩斿洖鍋囨暟鎹???
    璁捐?鑳屾櫙锛?    - 璇勬祴 Sandbox 妯?紡涓嬩笉鍏佽?鐪熷疄缃戠粶璇锋眰鍜屾枃浠惰?鍙栵紝
      浣嗚瘎娴嬮泦涓?父瑙?"璇锋?绱?浉鍏虫枃妗ｅ苟鍥炵瓟" 绫?prompt銆?      娌?湁杩欎釜宸?叿锛孉gent 浼氬弽澶嶅皾璇曡皟鐢?笉瀛樺湪鐨?search/retrieve API锛?      鏈?缁堣秴鏃舵垨杩斿洖绌虹粨鏋滐紝涓?噸褰卞搷璇勬祴鍑嗙?鎬???    - 杩斿洖缁撴灉鏍煎紡鍙傝?冧簡鐪熷疄鐨勫悜閲忔?绱?API 鍝嶅簲浣?(Elasticsearch / Milvus)锛?      纭?繚 Agent 鑳芥?纭??鏋?"documents" 瀛楁?銆?
    鍙傛暟锛?        query:  妫?绱?煡璇?瓧绗︿覆
        top_k:  杩斿洖缁撴灉鏁伴噺 (榛樿? 3锛屾渶澶?10)

    杩斿洖锛?        JSON 瀛楃?涓诧紝鍖呭惈 simulated_documents 鏁扮粍
    """
    q = (query or kwargs.get("q") or kwargs.get("text") or "").strip()
    if not q:
        return '{"error": "empty query", "documents": []}'

    # top_k 瀹夊叏闄愬埗锛氶槻 OOM 鍜屾伓鎰忓?鍙傛暟
    k = min(max(int(top_k or 3), 1), 10)

    if k > 5:
        logger.warning(
            "tool_retrieve_simulate: simulated overload (top_k=%d > 5), returning degraded response", k
        )
        return json.dumps(
            {"error": "retrieve_service_overload", "fallback": "try later"},
            ensure_ascii=False,
        )

    # 鍩轰簬鏌??鐢熸垚鍋囨枃妗ｅ垪琛?鈥斺??姣忎釜鏂囨?妯?嫙鐪熷疄妫?绱?粨鏋滅殑瀛楁?
    docs = []
    for i in range(k):
        docs.append(
            {
                "id": f"sim_doc_{i+1:04d}",
                "score": round(0.95 - i * 0.08, 4),
                "title": f"Simulated doc about {q[:30]} #{i+1}",
                "snippet": (
                    f"This is simulated search result #{i+1} for query '{q[:50]}'. "
                    f"In production, this would return actual vector DB hits. "
                    f"Currently in Sandbox mode, all results are deterministic mock data."
                ),
                "source": "sandbox_retriever",
            }
        )

    result = json.dumps(
        {"query": q, "top_k": k, "documents": docs},
        ensure_ascii=False,
    )
    return result[:MAX_OUTPUT_CHARS]

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
            "expression": {
                "type": "string",
                "description": "Math expression, e.g. (1+2)*3",
            },
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
            "timezone_name": {
                "type": "string",
                "description": "Ignored; always UTC in sandbox",
            },
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
    "time_query": {
        "description": "Get current Unix timestamp or ISO datetime string",
        "parameters": {
            "format": {
                "type": "string",
                "description": "Output format: unix / unix_ms / iso",
                "enum": ["unix", "unix_ms", "iso"],
            },
        },
        "required": [],
        "fn": tool_time_query,
    },
    "retrieve_simulate": {
        "description": "Simulated vector search returning mock documents (Sandbox safe)",
        "parameters": {
            "query": {"type": "string", "description": "妫?绱?煡璇?瓧绗︿覆"},
            "top_k": {
                "type": "integer",
                "description": "杩斿洖缁撴灉鏁伴噺 (榛樿?3锛屾渶澶?0)",
                "default": 3,
            },
        },
        "required": ["query"],
        "fn": tool_retrieve_simulate,
    },
}


def get_openai_tool_defs(names: list[str] | None = None) -> list[dict[str, Any]]:
    """Return OpenAI-format tool definitions (built-in + active plugin tools)."""
    selected = list(names) if names is not None else list(BUILTIN_TOOLS.keys())
    if names is None:
        try:
            from app.core.plugins.registry import get_capability_registry

            for t in get_capability_registry().list_tools():
                if t["name"] not in selected:
                    selected.append(t["name"])
        except Exception:
            pass

    plugin_tools: dict[str, Any] = {}
    try:
        from app.core.plugins.registry import get_capability_registry

        for t in get_capability_registry().list_tools():
            plugin_tools[t["name"]] = t
    except Exception:
        pass

    out: list[dict[str, Any]] = []
    for name in selected:
        meta = BUILTIN_TOOLS.get(name)
        if meta:
            out.append(
                {
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
                }
            )
            continue
        pmeta = plugin_tools.get(name)
        if pmeta:
            out.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": pmeta.get("description")
                        or f"Plugin tool: {name}",
                        "parameters": {
                            "type": "object",
                            "properties": pmeta.get("parameters") or {},
                            "required": pmeta.get("required") or [],
                        },
                    },
                }
            )
            continue
        # Unknown expected tool: still expose a stub definition for the model
        out.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": f"Tool: {name}",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }
        )
    return out


def get_tool_function(name: str) -> Callable[..., str] | None:
    meta = BUILTIN_TOOLS.get(name)
    if meta:
        return meta["fn"]
    # Plugin-provided tools
    try:
        from app.core.plugins.registry import get_capability_registry

        return get_capability_registry().get_tool_fn(name)
    except Exception:
        return None


def list_all_tool_names() -> list[str]:
    """Built-in + active plugin tool names."""
    names = set(BUILTIN_TOOLS.keys())
    try:
        from app.core.plugins.registry import get_capability_registry

        for t in get_capability_registry().list_tools():
            names.add(t["name"])
    except Exception:
        pass
    return sorted(names)


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

    # Optional pre_tool hooks (plugins); may mutate args via returned dict
    try:
        from app.core.plugins.base import HOOK_PRE_TOOL
        from app.core.plugins.hooks import get_hook_registry

        results = get_hook_registry().emit_sync(
            HOOK_PRE_TOOL, {"name": name, "args": dict(args)}
        )
        for r in results:
            if isinstance(r, dict) and isinstance(r.get("args"), dict):
                args = r["args"]
    except Exception:
        pass

    fn = custom_fn or get_tool_function(name)
    if fn is None:
        available = list_all_tool_names()
        msg = (
            f"[Sandbox] Tool '{name}' is not registered. "
            f"Available: {', '.join(available)}."
        )
        try:
            from app.core.observability.aols import LogEvent, emit_tool

            emit_tool(
                LogEvent.TOOL_FAILED,
                tool_name=name,
                success=False,
                input_data=args,
                error_message=msg,
            )
        except Exception:
            pass
        return msg

    try:
        from app.core.observability.aols import LogEvent, emit_tool

        emit_tool(LogEvent.TOOL_STARTED, tool_name=name, input_data=args)
    except Exception:
        pass

    import time as _time

    _t0 = _time.monotonic()

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
        latency = int((_time.monotonic() - _t0) * 1000)
        try:
            from app.core.observability.aols import LogEvent, emit_tool

            emit_tool(
                LogEvent.TOOL_TIMEOUT,
                tool_name=name,
                latency_ms=latency,
                success=False,
                input_data=args,
                error_message=f"timeout after {timeout_sec}s",
            )
        except Exception:
            pass
        return f"[Sandbox] Tool '{name}' timed out after {timeout_sec}s"
    except Exception as exc:
        latency = int((_time.monotonic() - _t0) * 1000)
        logger.warning("Tool %s failed: %s", name, exc)
        try:
            from app.core.observability.aols import LogEvent, emit_tool

            emit_tool(
                LogEvent.TOOL_FAILED,
                tool_name=name,
                latency_ms=latency,
                success=False,
                input_data=args,
                error_message=str(exc),
            )
        except Exception:
            pass
        return f"[Sandbox] Tool '{name}' error: {exc}"

    text = str(result)
    if len(text) > MAX_OUTPUT_CHARS:
        text = text[:MAX_OUTPUT_CHARS] + "鈥?truncated]"

    latency = int((_time.monotonic() - _t0) * 1000)
    try:
        from app.core.observability.aols import LogEvent, emit_tool

        emit_tool(
            LogEvent.TOOL_COMPLETED,
            tool_name=name,
            latency_ms=latency,
            success=True,
            input_data=args,
            output_data=text,
        )
    except Exception:
        pass

    try:
        from app.core.plugins.base import HOOK_POST_TOOL
        from app.core.plugins.hooks import get_hook_registry

        get_hook_registry().emit_sync(
            HOOK_POST_TOOL, {"name": name, "args": args, "output": text}
        )
    except Exception:
        pass
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


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in tool implementations
# ---------------------------------------------------------------------------

def _web_search(query: str, max_results: int = 3) -> str:
    """Placeholder web search 鈥?returns a stub result."""
    return json.dumps({
        "query": query,
        "results": [f"[stub] Result {i} for '{query}'" for i in range(1, max_results + 1)],
    })



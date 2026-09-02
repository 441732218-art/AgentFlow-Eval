# AgentFlow Intelligence v2.0 — Trade Application Provider tests (Phase 9.1)

from __future__ import annotations

from pathlib import Path

from app.applications.bootstrap import bootstrap_applications
from app.applications.trade_provider.tools import TOOL_DEFINITIONS
from app.runtime.tools.factory import create_tool_execution_engine
from app.runtime.tools.local_handler_registry import LocalHandlerRegistry
from app.runtime.tools.registry import create_tool_registry

_RUNTIME_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime"
_RUNTIME_CORE_EXCLUDED_PARTS = frozenset({"service"})
_FORBIDDEN_TRADE_RUNTIME_STRINGS = (
    "trade_provider",
    "trade.search_customer",
    "trade.generate_email",
    "trade.create_followup",
)


def test_trade_provider_registers_tools() -> None:
    registry = create_tool_registry(bootstrap=False)
    handlers = LocalHandlerRegistry()
    bootstrap_applications(registry, handlers)

    names = {item["name"] for item in registry.list_tools()}
    assert {
        "trade.search_customer",
        "trade.generate_email",
        "trade.create_followup",
    }.issubset(names)


def test_trade_tool_definitions_exist() -> None:
    assert len(TOOL_DEFINITIONS) == 3
    by_name = {definition.name: definition for definition in TOOL_DEFINITIONS}

    assert by_name["trade.search_customer"].executor_type == "remote"
    assert by_name["trade.search_customer"].metadata == {
        "provider": "trade",
        "category": "customer",
    }

    assert by_name["trade.generate_email"].executor_type == "local"
    assert by_name["trade.generate_email"].metadata == {
        "provider": "trade",
        "category": "email",
    }

    assert by_name["trade.create_followup"].executor_type == "remote"
    assert by_name["trade.create_followup"].metadata == {
        "provider": "trade",
        "category": "followup",
    }


def test_trade_generate_email_executes_via_local_handler_registry() -> None:
    registry = create_tool_registry(bootstrap=False)
    handlers = LocalHandlerRegistry()
    bootstrap_applications(registry, handlers)
    engine = create_tool_execution_engine(handler_registry=handlers)

    definition = registry.get("trade.generate_email")
    result = engine.execute(
        definition,
        {
            "customer": "ABC",
            "product": "AI Software",
            "language": "en",
        },
    )

    assert result.tool_name == "trade.generate_email"
    assert result.executor_type == "local"
    assert "subject" in result.output
    assert "body" in result.output
    assert "ABC" in result.output["subject"]
    assert "AI Software" in result.output["body"]


def test_trade_remote_tools_have_definition_only_no_local_handler() -> None:
    registry = create_tool_registry(bootstrap=False)
    handlers = LocalHandlerRegistry()
    bootstrap_applications(registry, handlers)

    assert registry.get("trade.search_customer").executor_type == "remote"
    assert registry.get("trade.create_followup").executor_type == "remote"
    assert handlers.get("trade.search_customer") is None
    assert handlers.get("trade.create_followup") is None
    assert handlers.get("trade.generate_email") is not None


def test_runtime_core_has_no_trade_provider_references() -> None:
    for path in _RUNTIME_ROOT.rglob("*.py"):
        relative_parts = path.relative_to(_RUNTIME_ROOT).parts
        if relative_parts and relative_parts[0] in _RUNTIME_CORE_EXCLUDED_PARTS:
            continue
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_TRADE_RUNTIME_STRINGS:
            assert forbidden not in source, f"{forbidden!r} found in {path}"

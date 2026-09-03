# AgentFlow Intelligence v2.0 — Tool capability registry tests (Phase 10.12)

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from app.runtime.tool_registry.errors import ToolDisabledError, ToolNotFoundError
from app.runtime.tool_registry.memory_registry import InMemoryToolRegistry
from app.runtime.tool_registry.models import ToolCapability
from app.runtime.tool_registry.registry import resolve_tool_capability

_TOOL_REGISTRY_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "tool_registry"
)
_FORBIDDEN_STRINGS = (
    "app.applications",
    "app.api",
    "app.service",
    "app.tracing",
    "app.runtime.memory",
    "openai",
    "langgraph",
    "sqlalchemy",
    "postgres",
    "redis",
    "httpx",
)


def _capability(
    tool_name: str = "email.send",
    *,
    version: str = "1.0",
    enabled: bool = True,
) -> ToolCapability:
    return ToolCapability(
        tool_name=tool_name,
        version=version,
        description="Send email",
        capability_tags=("communication",),
        permission_scope=("email.send",),
        enabled=enabled,
        metadata={"channel": "email"},
    )


def test_tool_capability_creation() -> None:
    capability = _capability()

    assert capability.tool_name == "email.send"
    assert capability.version == "1.0"
    assert capability.capability_tags == ("communication",)
    assert capability.permission_scope == ("email.send",)
    assert capability.enabled is True
    assert capability.metadata["channel"] == "email"


def test_tool_capability_update_returns_new_immutable_instance() -> None:
    capability = _capability()
    updated = capability.with_updates(version="2.0", enabled=False)

    assert updated is not capability
    assert updated.version == "2.0"
    assert updated.enabled is False
    assert capability.version == "1.0"
    assert capability.enabled is True


def test_in_memory_tool_registry_register_and_get() -> None:
    registry = InMemoryToolRegistry()
    capability = _capability()

    registry.register(capability)

    assert registry.get("email.send") == capability


def test_in_memory_tool_registry_list_tools() -> None:
    registry = InMemoryToolRegistry()
    registry.register(_capability("email.send"))
    registry.register(_capability("crm.lookup", version="1.1"))

    tools = registry.list_tools()

    assert {tool.tool_name for tool in tools} == {"email.send", "crm.lookup"}


def test_in_memory_tool_registry_remove_tool() -> None:
    registry = InMemoryToolRegistry()
    registry.register(_capability())

    registry.remove("email.send")

    assert registry.get("email.send") is None


def test_in_memory_tool_registry_replaces_duplicate_registration() -> None:
    registry = InMemoryToolRegistry()
    registry.register(_capability(version="1.0"))
    updated = _capability(version="2.0")

    registry.register(updated)

    stored = registry.get("email.send")
    assert stored is not None
    assert stored.version == "2.0"


def test_resolve_tool_capability_rejects_disabled_tool() -> None:
    registry = InMemoryToolRegistry()
    registry.register(_capability(enabled=False))

    with pytest.raises(ToolDisabledError, match="email.send"):
        resolve_tool_capability(registry, "email.send")


def test_resolve_tool_capability_raises_for_missing_tool() -> None:
    registry = InMemoryToolRegistry()

    with pytest.raises(ToolNotFoundError, match="missing.tool"):
        resolve_tool_capability(registry, "missing.tool")


def test_in_memory_tool_registry_is_thread_safe() -> None:
    registry = InMemoryToolRegistry()
    errors: list[Exception] = []

    def worker(index: int) -> None:
        try:
            tool_name = f"tool.thread.{index}"
            registry.register(_capability(tool_name))
            assert registry.get(tool_name) is not None
            registry.list_tools()
            registry.remove(tool_name)
        except Exception as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []


def test_tool_registry_has_no_forbidden_dependencies() -> None:
    for path in _TOOL_REGISTRY_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

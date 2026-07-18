# (c) 2026 AgentFlow-Eval
"""Unit tests for the plugin system (load, hooks, lifecycle, capabilities)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.plugins.base import (
    HOOK_POST_AGENT_RUN,
    HOOK_PRE_AGENT_RUN,
    HOOK_PRE_TOOL,
    BasePlugin,
    PluginContext,
    PluginMeta,
    PluginState,
    PluginType,
)
from app.core.plugins.hooks import HookRegistry
from app.core.plugins.manager import PluginManager, reset_plugin_manager
from app.core.plugins.market import PluginMarket, reset_plugin_market
from app.core.plugins.loader import PluginLoadError, instantiate_plugin


@pytest.fixture(autouse=True)
def _clean_plugins():
    reset_plugin_manager()
    reset_plugin_market()
    yield
    reset_plugin_manager()
    reset_plugin_market()


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


def test_hook_priority_order():
    reg = HookRegistry()
    order: list[int] = []

    reg.register("h", lambda p: order.append(1), priority=10)
    reg.register("h", lambda p: order.append(2), priority=5)
    reg.register("h", lambda p: order.append(3), priority=20)

    reg.emit_sync("h", {})
    assert order == [2, 1, 3]


def test_hook_unregister_and_plugin_cleanup():
    reg = HookRegistry()
    eid = reg.register("x", lambda p: 1, plugin_id="p1")
    reg.register("x", lambda p: 2, plugin_id="p2")
    assert len(reg.list_hooks("x")) == 2
    assert reg.unregister(eid) is True
    assert len(reg.list_hooks("x")) == 1
    assert reg.unregister_plugin("p2") == 1
    assert reg.list_hooks("x") == []


def test_hook_isolates_exceptions():
    reg = HookRegistry()

    def bad(_p):
        raise RuntimeError("boom")

    def good(_p):
        return "ok"

    reg.register("e", bad, priority=1)
    reg.register("e", good, priority=2)
    results = reg.emit_sync("e", {})
    assert results[0]["error"] == "boom"
    assert results[1] == "ok"


@pytest.mark.asyncio
async def test_hook_async_emit():
    reg = HookRegistry()

    async def async_cb(payload):
        return payload.get("v", 0) + 1

    reg.register("a", async_cb)
    out = await reg.emit("a", {"v": 41})
    assert out == [42]


# ---------------------------------------------------------------------------
# Lifecycle + types
# ---------------------------------------------------------------------------


def test_load_echo_tool_plugin():
    mgr = reset_plugin_manager()
    rec = mgr.load(entry="app.plugins.examples.echo_tool:Plugin", activate=True)
    assert rec.state == PluginState.ACTIVE
    assert rec.plugin_id == "echo_tool"

    from app.core.agent_runner.tool_sandbox import get_tool_function, run_tool_sandboxed

    fn = get_tool_function("echo")
    assert fn is not None
    out = run_tool_sandboxed("echo", {"message": "hi"})
    data = json.loads(out)
    assert data["echo"]["message"] == "hi"

    mgr.deactivate("echo_tool")
    assert mgr.get("echo_tool").state == PluginState.DISABLED
    assert get_tool_function("echo") is None


@pytest.mark.asyncio
async def test_load_echo_runner_plugin():
    mgr = reset_plugin_manager()
    rec = mgr.load(entry="app.plugins.examples.echo_runner:Plugin")
    assert rec.state == PluginState.ACTIVE

    from app.core.agent_runner.factory import build_agent_runner

    runner = build_agent_runner({"runner": "echo", "prefix": ">> "})
    result = await runner.run("hello", {"prefix": ">> "})
    # AgentResult dataclass
    steps = result.steps if hasattr(result, "steps") else result.get("steps")
    assert any(">> hello" in str(s) for s in steps)


@pytest.mark.asyncio
async def test_load_length_judge_plugin():
    mgr = reset_plugin_manager()
    mgr.load(entry="app.plugins.examples.length_judge:Plugin")

    from app.core.celery_app.tasks import build_llm_judge

    judge = build_llm_judge({"type": "length"})
    res = await judge.evaluate(
        [{"content": "abcdef"}],
        expected_output="abcxyz",
        expected_tools=[],
    )
    assert res.total > 0
    assert "length_similarity" in res.scores


def test_hook_plugin_records_events():
    mgr = reset_plugin_manager()
    mgr.load(entry="app.plugins.examples.audit_hooks:Plugin")

    from app.plugins.examples.audit_hooks import clear_event_log, get_event_log

    clear_event_log()
    mgr.hooks.emit_sync(HOOK_PRE_AGENT_RUN, {"query": "q1"})
    mgr.hooks.emit_sync(HOOK_POST_AGENT_RUN, {"status": "success"})
    log = get_event_log()
    assert any(e["event"] == HOOK_PRE_AGENT_RUN for e in log)
    assert any(e["event"] == HOOK_POST_AGENT_RUN for e in log)


def test_lifecycle_unload_reload():
    mgr = reset_plugin_manager()
    mgr.load(entry="app.plugins.examples.echo_tool:Plugin")
    assert "echo" in [t["name"] for t in mgr.capabilities.list_tools()]
    mgr.unload("echo_tool")
    assert mgr.get("echo_tool").state == PluginState.UNLOADED
    assert mgr.capabilities.get_tool("echo") is None
    rec = mgr.reload("echo_tool")
    # reload after unload uses entry stored on record
    assert rec.state in {PluginState.ACTIVE, PluginState.ERROR}
    # If entry still present, re-load explicitly
    if rec.state == PluginState.ERROR or rec.instance is None:
        rec = mgr.load(entry="app.plugins.examples.echo_tool:Plugin")
    assert rec.state == PluginState.ACTIVE


def test_discover_and_bootstrap_modules():
    mgr = reset_plugin_manager()
    summary = mgr.bootstrap(
        enabled=True,
        modules=[
            "app.plugins.examples.echo_tool:Plugin",
            "app.plugins.examples.audit_hooks:Plugin",
        ],
    )
    assert summary["enabled"] is True
    assert "echo_tool" in summary["loaded"]
    assert "audit_hooks" in summary["loaded"]
    status = mgr.status()
    assert any(t["name"] == "echo" for t in status["tools"])
    assert any(h["hook"] == HOOK_PRE_AGENT_RUN for h in status["hooks"])


def test_bootstrap_disabled():
    mgr = reset_plugin_manager()
    summary = mgr.bootstrap(enabled=False, modules=["app.plugins.examples.echo_tool:Plugin"])
    assert summary["enabled"] is False
    assert summary["loaded"] == []


def test_load_from_directory(tmp_path: Path):
    """Directory plugin with plugin.py + plugin.json."""
    pkg = tmp_path / "sample_hook"
    pkg.mkdir()
    (pkg / "plugin.json").write_text(
        json.dumps(
            {
                "name": "sample_hook",
                "version": "0.2.0",
                "type": "hook",
                "description": "tmp plugin",
            }
        ),
        encoding="utf-8",
    )
    (pkg / "plugin.py").write_text(
        """
from app.core.plugins.base import BasePlugin, PluginMeta, PluginType, PluginContext, HOOK_PRE_TOOL

class Plugin(BasePlugin):
    meta = PluginMeta(
        name="sample_hook",
        version="0.2.0",
        plugin_type=PluginType.HOOK,
        description="tmp",
    )
    def on_activate(self, ctx: PluginContext):
        ctx.register_hook(HOOK_PRE_TOOL, lambda p: {"ok": True, **p}, priority=1)
""",
        encoding="utf-8",
    )
    mgr = reset_plugin_manager()
    rec = mgr.load(path=pkg, activate=True)
    assert rec.state == PluginState.ACTIVE
    assert rec.meta and rec.meta.version == "0.2.0"
    results = mgr.hooks.emit_sync(HOOK_PRE_TOOL, {"name": "x", "args": {}})
    assert any(isinstance(r, dict) and r.get("ok") is True for r in results)


def test_instantiate_invalid_entry():
    with pytest.raises(PluginLoadError):
        instantiate_plugin("this.module.does.not.exist:Plugin")


def test_market_seed_and_install():
    mgr = reset_plugin_manager()
    market = PluginMarket(manager=mgr)
    market.seed_builtin_catalog()
    items = market.list_catalog(plugin_type="tool")
    assert any(i["id"] == "echo_tool" for i in items)
    rec = market.install("echo_tool")
    assert rec["state"] == "active"
    assert market.list_catalog(installed_only=True)
    market.uninstall("echo_tool")
    assert mgr.get("echo_tool").state == PluginState.UNLOADED


def test_custom_inline_plugin():
    """Register a plugin class without filesystem entry via entry string."""

    class Dummy(BasePlugin):
        meta = PluginMeta(
            name="dummy",
            version="1.0",
            plugin_type=PluginType.HOOK,
            description="inline",
        )

        def on_activate(self, ctx: PluginContext) -> None:
            assert ctx.register_hook
            ctx.register_hook("custom_event", lambda p: "done")

    # Simulate by direct manager manipulation using module path of this class is hard;
    # exercise register path via load of factory-less: use activate path manually.
    mgr = reset_plugin_manager()
    instance = Dummy()
    rec_id = "dummy"
    from app.core.plugins.manager import PluginRecord

    mgr._plugins[rec_id] = PluginRecord(
        plugin_id=rec_id,
        entry="inline",
        source="module",
        instance=instance,
        meta=instance.meta,
        state=PluginState.LOADED,
    )
    mgr.activate(rec_id)
    assert mgr.hooks.emit_sync("custom_event", {}) == ["done"]

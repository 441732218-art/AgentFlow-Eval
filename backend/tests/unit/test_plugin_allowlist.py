# (c) 2026 AgentFlow-Eval
from app.core.plugins.manager import PluginManager, reset_plugin_manager


def test_bootstrap_allowlist_skips_unknown():
    mgr = reset_plugin_manager()
    summary = mgr.bootstrap(
        enabled=True,
        modules=[
            "app.plugins.examples.echo_tool:Plugin",
            "app.plugins.examples.audit_hooks:Plugin",
        ],
        allowlist=["app.plugins.examples.echo_tool"],
        auto_activate=True,
    )
    assert "echo_tool" in summary["loaded"]
    assert "audit_hooks" in summary.get("skipped_allowlist", []) or (
        "audit_hooks" not in summary["loaded"]
    )


def test_strict_empty_modules_loads_none():
    mgr = reset_plugin_manager()
    summary = mgr.bootstrap(
        enabled=True,
        directories=[],
        modules=[],
        allowlist=["only.this"],
    )
    assert summary["loaded"] == []

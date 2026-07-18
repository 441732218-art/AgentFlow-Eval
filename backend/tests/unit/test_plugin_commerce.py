# (c) 2026 AgentFlow-Eval
from app.core.plugins.commerce import PluginCommerceMeta, check_entitlement
from app.core.plugins.sandbox import PluginSandboxPolicy, validate_activate
from app.core.plugins.versioning import check_core_requirement, satisfies


def test_semver_satisfies():
    assert satisfies("0.1.0", ">=0.1.0")
    assert satisfies("0.2.0", ">=0.1.0")
    assert not satisfies("0.0.9", ">=0.1.0")
    assert satisfies("1.0.0", "*")


def test_core_requirement():
    ok, _ = check_core_requirement(">=0.1.0")
    assert ok is True
    ok2, msg = check_core_requirement(">=99.0.0")
    assert ok2 is False
    assert "does not satisfy" in msg


def test_commerce_entitlement():
    free = PluginCommerceMeta(price_cents=0)
    ok, _ = check_entitlement(free, plan_code="free", plugin_id="echo_tool")
    assert ok

    paid = PluginCommerceMeta(
        price_cents=999, entitlement_plan=["pro", "enterprise"], is_paid=True
    )
    ok2, reason = check_entitlement(paid, plan_code="free", plugin_id="paid_x")
    assert ok2 is False
    ok3, _ = check_entitlement(paid, plan_code="pro", plugin_id="paid_x")
    assert ok3 is True


def test_sandbox_validate():
    pol = PluginSandboxPolicy(permissions=["system:config"])
    ok, _ = validate_activate(pol, rbac_enforced=False)
    assert ok
    ok2, msg = validate_activate(
        pol, actor_permissions={"task:read"}, rbac_enforced=True
    )
    assert ok2 is False
    assert "missing" in msg

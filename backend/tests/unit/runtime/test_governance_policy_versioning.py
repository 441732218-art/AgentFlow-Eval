# AgentFlow Intelligence v2.0 — Runtime governance policy versioning tests (Phase 11.8)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.runtime.governance.versioning.memory_registry import InMemoryGovernancePolicyRegistry
from app.runtime.governance.versioning.models import GovernancePolicyVersion

_VERSIONING_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "versioning"
)
_FORBIDDEN_STRINGS = (
    "app.applications",
    "app.api",
    "app.service",
    "app.tracing",
    "app.runtime.memory",
    "app.core",
    "openai",
    "langgraph",
    "sqlalchemy",
    "postgres",
    "trade_provider",
    "kafka",
    "redis",
    "PolicyEngine",
    "PermissionEvaluator",
    "GovernanceEvaluator",
    "InMemoryGovernanceEngine",
    "GovernanceEnforcer",
    "AgentRuntime",
    "AgentExecutionPipeline",
    "EvidenceCollector",
    "EvidenceQueryService",
)


def _policy(
    *,
    policy_id: str = "policy-1",
    version: str = "1.0.0",
    status: str = "ACTIVE",
    name: str = "Default Policy",
    description: str | None = "baseline policy",
) -> GovernancePolicyVersion:
    return GovernancePolicyVersion(
        policy_id=policy_id,
        version=version,
        name=name,
        description=description,
        status=status,  # type: ignore[arg-type]
        metadata={"owner": "governance"},
    )


def test_create_policy_version() -> None:
    policy = _policy()

    assert policy.policy_id == "policy-1"
    assert policy.version == "1.0.0"
    assert policy.name == "Default Policy"
    assert policy.status == "ACTIVE"
    assert policy.metadata["owner"] == "governance"
    assert policy.created_at is not None


def test_policy_version_is_immutable() -> None:
    policy = _policy()

    with pytest.raises(FrozenInstanceError):
        policy.status = "DISABLED"  # type: ignore[misc]

    updated = policy.with_updates(status="DISABLED")
    assert updated.status == "DISABLED"
    assert policy.status == "ACTIVE"


def test_register_policy_version() -> None:
    registry = InMemoryGovernancePolicyRegistry()
    policy = _policy()

    registry.register(policy)

    assert registry.get("policy-1", "1.0.0") == policy


def test_get_by_policy_id_and_version() -> None:
    registry = InMemoryGovernancePolicyRegistry()
    registry.register(_policy(version="1.0.0"))
    registry.register(_policy(version="1.1.0", name="Updated Policy"))

    assert registry.get("policy-1", "1.1.0") is not None
    assert registry.get("policy-1", "9.9.9") is None
    assert registry.get("missing-policy", "1.0.0") is None


def test_replace_duplicate_version() -> None:
    registry = InMemoryGovernancePolicyRegistry()
    original = _policy(description="first")
    replacement = _policy(description="second")

    registry.register(original)
    registry.register(replacement)

    stored = registry.get("policy-1", "1.0.0")
    assert stored is not None
    assert stored.description == "second"
    assert len(registry.list_versions("policy-1")) == 1


def test_list_versions() -> None:
    registry = InMemoryGovernancePolicyRegistry()
    registry.register(_policy(version="1.0.0"))
    registry.register(_policy(version="1.2.0"))
    registry.register(_policy(version="1.10.0"))

    versions = [policy.version for policy in registry.list_versions("policy-1")]

    assert versions == ["1.0.0", "1.2.0", "1.10.0"]


def test_remove_version() -> None:
    registry = InMemoryGovernancePolicyRegistry()
    registry.register(_policy(version="1.0.0"))
    registry.register(_policy(version="2.0.0"))

    registry.remove("policy-1", "1.0.0")

    assert registry.get("policy-1", "1.0.0") is None
    assert registry.get("policy-1", "2.0.0") is not None


def test_get_latest_active_version() -> None:
    registry = InMemoryGovernancePolicyRegistry()
    registry.register(_policy(version="1.0.0", status="DEPRECATED"))
    registry.register(_policy(version="1.5.0", status="ACTIVE"))
    registry.register(_policy(version="2.0.0", status="DRAFT"))

    latest = registry.get_latest("policy-1")

    assert latest is not None
    assert latest.version == "1.5.0"
    assert latest.status == "ACTIVE"


def test_semantic_version_ordering() -> None:
    registry = InMemoryGovernancePolicyRegistry()
    registry.register(_policy(version="1.0.0", status="ACTIVE"))
    registry.register(_policy(version="1.0.10", status="ACTIVE"))
    registry.register(_policy(version="1.0.9", status="ACTIVE"))
    registry.register(_policy(version="2.0.0-beta", status="ACTIVE"))

    latest = registry.get_latest("policy-1")

    assert latest is not None
    assert latest.version == "1.0.10"


def test_registry_is_thread_safe() -> None:
    registry = InMemoryGovernancePolicyRegistry()
    errors: list[Exception] = []

    def register_many(prefix: str) -> None:
        try:
            for index in range(20):
                registry.register(
                    _policy(
                        policy_id=f"policy-{prefix}",
                        version=f"1.{index}.0",
                        name=f"{prefix}-{index}",
                    )
                )
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=register_many, args=(f"t{i}",)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(registry.list_versions("policy-t0")) == 20


def test_versioning_module_has_no_forbidden_dependencies() -> None:
    for path in _VERSIONING_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"

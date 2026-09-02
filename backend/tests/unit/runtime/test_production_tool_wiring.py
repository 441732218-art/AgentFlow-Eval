# AgentFlow Intelligence v2.0 — Production tool wiring tests (Phase 8.8)

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.context import RuntimeContext
from app.runtime.executor import attach_tool_request
from app.runtime.service import (
    RuntimeService,
    is_production_tooling_bootstrapped,
    reset_production_tooling,
)
from app.runtime.tools.registry import get_tool_registry

_RUNTIME_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime"
_RUNTIME_CORE_EXCLUDED_PARTS = frozenset({"service"})
_FORBIDDEN_RUNTIME_CORE_STRINGS = (
    "example_provider",
    "app.applications",
    "app_example.echo",
    "app_example.remote_search",
)


@pytest.fixture(autouse=True)
def _reset_production_wiring() -> None:
    reset_production_tooling()
    yield
    reset_production_tooling()


def test_runtime_core_excludes_service_from_application_leakage_scan() -> None:
    for path in _RUNTIME_ROOT.rglob("*.py"):
        relative_parts = path.relative_to(_RUNTIME_ROOT).parts
        if relative_parts and relative_parts[0] in _RUNTIME_CORE_EXCLUDED_PARTS:
            continue
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_RUNTIME_CORE_STRINGS:
            assert forbidden not in source, f"{forbidden!r} found in {path}"


def test_production_bootstrap_runs_once_without_duplicate_error() -> None:
    service_one = RuntimeService()
    service_two = RuntimeService()

    assert is_production_tooling_bootstrapped()
    assert service_one.executor.tool_registry is service_two.executor.tool_registry
    registry = get_tool_registry()
    assert registry.get("app_example.echo").name == "app_example.echo"
    assert registry.get("example.echo").name == "example.echo"


def test_production_runtime_executes_app_example_echo_end_to_end() -> None:
    service = RuntimeService()
    registry = service.executor.tool_registry
    assert registry is not None

    definition = registry.get("app_example.echo")
    context = attach_tool_request(
        RuntimeContext(execution_id="prod-exec-1", agent_id="agent-prod"),
        definition,
        {"message": "production-wiring"},
    )

    dto = service.execute(
        agent_id="agent-prod",
        task="execute application tool",
        context=context,
    )

    assert dto.status == "SUCCESS"
    assert dto.output == {"app_echo": "production-wiring"}
    assert dto.execution_id == "prod-exec-1"
    assert service.executor.pipeline.tool_execution_engine is not None

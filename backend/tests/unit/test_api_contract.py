# (c) 2026 AgentFlow-Eval
"""API v1 freeze: OpenAPI must not remove frozen path+method pairs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FROZEN = ROOT.parent / "docs" / "openapi-v1.json"
# When running from backend/, docs is sibling
if not FROZEN.exists():
    FROZEN = ROOT / ".." / "docs" / "openapi-v1.json"
FROZEN = FROZEN.resolve()

# Minimal freeze set always enforced even if openapi file missing
CORE_V1_OPS = {
    ("/api/v1/me", "get"),
    ("/api/v1/tasks", "get"),
    ("/api/v1/tasks", "post"),
    ("/api/v1/tasks/{task_id}", "get"),
    ("/api/v1/dashboard", "get"),
    ("/api/v1/traces", "get"),
    ("/api/v1/tenants", "get"),
    ("/api/v1/tenants", "post"),
    ("/health", "get"),
    ("/health/ready", "get"),
}


def _path_methods(schema: dict) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for path, item in (schema.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method, _op in item.items():
            if method.lower() in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "head",
                "options",
            }:
                out.add((path, method.lower()))
    return out


class TestApiContractFreeze:
    def test_core_ops_present_in_live_openapi(self) -> None:
        from app.main import app

        live = _path_methods(app.openapi())
        missing = CORE_V1_OPS - live
        assert not missing, f"Missing frozen core ops: {sorted(missing)}"

    def test_frozen_file_no_removals(self) -> None:
        if not FROZEN.is_file():
            pytest.skip(f"frozen openapi not found: {FROZEN}")
        from app.main import app
        from scripts.export_openapi import check_compatible

        frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
        current = app.openapi()
        errors = check_compatible(frozen, current)
        assert not errors, "\n".join(errors)

    def test_export_helper_roundtrip(self) -> None:
        from scripts.export_openapi import check_compatible, export_schema, path_methods

        schema = export_schema()
        assert len(path_methods(schema)) >= len(CORE_V1_OPS)
        assert check_compatible(schema, schema) == []

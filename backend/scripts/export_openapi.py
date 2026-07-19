# (c) 2026 AgentFlow-Eval
"""Export FastAPI OpenAPI schema and optionally check against frozen contract.

Usage:
  cd backend
  python scripts/export_openapi.py -o ../docs/openapi-v1.json
  python scripts/export_openapi.py --check ../docs/openapi-v1.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _app():
    # Ensure backend root on path
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from app.main import app

    return app


def export_schema() -> dict:
    return _app().openapi()


def path_methods(schema: dict) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for path, item in (schema.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method in item:
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


def check_compatible(frozen: dict, current: dict) -> list[str]:
    """Return list of breaking-change messages (empty = ok).

    Breaking: frozen (path, method) missing from current.
    Additive endpoints are allowed.
    """
    errors: list[str] = []
    frozen_pm = path_methods(frozen)
    current_pm = path_methods(current)
    missing = frozen_pm - current_pm
    for path, method in sorted(missing):
        errors.append(f"BREAKING: removed {method.upper()} {path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenAPI export / freeze check")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write OpenAPI JSON to this path",
    )
    parser.add_argument(
        "--check",
        type=Path,
        metavar="FROZEN_JSON",
        help="Fail if current schema removes paths from frozen JSON",
    )
    args = parser.parse_args(argv)

    schema = export_schema()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {args.output} ({len(path_methods(schema))} operations)")

    if args.check:
        frozen = json.loads(args.check.read_text(encoding="utf-8"))
        errors = check_compatible(frozen, schema)
        if errors:
            print("API compatibility check FAILED:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1
        print(
            f"API compatibility check OK "
            f"(frozen={len(path_methods(frozen))} ops, "
            f"current={len(path_methods(schema))} ops)"
        )

    if not args.output and not args.check:
        # dump to stdout
        json.dump(schema, sys.stdout, ensure_ascii=False, indent=2)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

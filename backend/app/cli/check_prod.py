# (c) 2026 AgentFlow-Eval
"""CLI: validate production configuration before deploy.

Usage::

    python -m app.cli.check_prod
    python -m app.cli.check_prod --strict   # treat warnings as failures
    make check-prod
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    """Run production settings validation and print a human-readable report.

    Returns:
        0 if OK (or only warnings without --strict), 1 on hard errors / strict warnings.
    """
    parser = argparse.ArgumentParser(
        description="Validate AgentFlow-Eval production configuration",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any warning is present (in addition to hard errors)",
    )
    parser.add_argument(
        "--force-prod",
        action="store_true",
        help="Apply production rules even when ENV is not prod",
    )
    args = parser.parse_args(argv)

    from app.config import settings
    from app.core.settings_guard import validate_settings

    print(f"ENV={settings.ENV} DEBUG={settings.DEBUG} APP={settings.APP_NAME}")
    print(
        f"DEPLOY_PROFILE={getattr(settings, 'DEPLOY_PROFILE', '?')} "
        f"BILLING_ENABLED={getattr(settings, 'BILLING_ENABLED', False)} "
        f"STRIPE_MODE={getattr(settings, 'STRIPE_MODE', 'mock')} "
        f"AUTH_ENABLED={getattr(settings, 'AUTH_ENABLED', False)}"
    )
    print("---")

    result = validate_settings(settings, strict=True if args.force_prod else None)

    # When not prod and not force, still show a note
    if not settings.is_prod and not args.force_prod:
        print("Note: ENV is not prod — running light checks only.")
        print("      Use --force-prod to simulate production validation.")
        print("---")

    # Soft guidance (always printed as INFO-style lines, not failures)
    profile = str(getattr(settings, "DEPLOY_PROFILE", "auto") or "auto").lower()
    db = str(getattr(settings, "DATABASE_URL", "") or "")
    if args.force_prod or settings.is_prod:
        if profile == "lite":
            result.warnings.append(
                "DEPLOY_PROFILE=lite is for demos; use private/saas for public production"
            )
        if "sqlite" in db:
            result.warnings.append(
                "DATABASE_URL uses SQLite — prefer PostgreSQL for multi-user production"
            )
        if (
            getattr(settings, "BILLING_ENABLED", False)
            and getattr(settings, "STRIPE_MODE", "mock") == "mock"
        ):
            result.warnings.append(
                "BILLING_ENABLED with STRIPE_MODE=mock — no real charges; set live keys for SaaS billing"
            )

    for w in result.warnings:
        print(f"WARNING: {w}")
    for e in result.errors:
        print(f"ERROR:   {e}")

    print("---")
    print("Health probes (ops):")
    print("  GET /health/live   — liveness")
    print("  GET /health/ready  — readiness (DB; Redis unless eager/lite)")
    print("  GET /health        — composite")
    print("  scripts/post-deploy-verify.ps1 -BaseUrl https://api.example.com")
    print("---")

    if not result.errors and not result.warnings:
        print("OK: configuration looks good.")
        return 0

    if result.errors:
        print("---")
        print(f"FAILED: {len(result.errors)} error(s)")
        return 1

    if args.strict and result.warnings:
        print("---")
        print(f"FAILED (strict): {len(result.warnings)} warning(s)")
        return 1

    print("---")
    print(f"OK with {len(result.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

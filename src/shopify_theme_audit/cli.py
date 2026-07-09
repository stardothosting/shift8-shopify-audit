from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ai import summarize_audit
from .config import DEFAULT_CONFIG_PATH, initialize_config, load_config
from .detector import audit_storefront
from .exporter import export_fixture


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "audit":
        audit = audit_storefront(args.url)
        if args.with_ai:
            config = load_config(args.config)
            provider = config.get_provider(args.provider)
            ai_summary = summarize_audit(audit, provider)
        else:
            ai_summary = None

        if args.format == "json":
            payload = audit.to_dict()
            if ai_summary:
                payload["ai_summary"] = ai_summary
            print(json.dumps(payload, indent=2))
        else:
            _print_human(audit, ai_summary)
        return 0

    if args.command == "init-config":
        path = initialize_config(args.path)
        print(f"Created config at {path}")
        return 0

    if args.command == "export-fixture":
        path = export_fixture(args.url, args.output)
        print(f"Wrote fixture bundle to {path}")
        return 0

    parser.print_help()
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shopify-theme-audit")
    subparsers = parser.add_subparsers(dest="command")

    audit_parser = subparsers.add_parser("audit", help="Audit a Shopify storefront")
    audit_parser.add_argument("url")
    audit_parser.add_argument("--format", choices=("text", "json"), default="text")
    audit_parser.add_argument("--with-ai", action="store_true")
    audit_parser.add_argument("--provider", default="openai")
    audit_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)

    init_config_parser = subparsers.add_parser("init-config", help="Create a secure local config template")
    init_config_parser.add_argument("--path", type=Path, default=DEFAULT_CONFIG_PATH)

    export_parser = subparsers.add_parser("export-fixture", help="Capture a storefront into a reusable fixture bundle")
    export_parser.add_argument("url")
    export_parser.add_argument("--output", type=Path, required=True)
    return parser


def _print_human(audit, ai_summary: str | None) -> None:
    print(f"URL: {audit.url}")
    print(f"Final URL: {audit.final_url}")
    print(f"Status: {audit.status_code}")
    print(f"Shopify detected: {'yes' if audit.shopify_detected else 'no'}")
    print(
        "Assessment: "
        f"{audit.assessment.classification} "
        f"(confidence {audit.assessment.confidence}, "
        f"customness {audit.assessment.customness_score}, "
        f"base {audit.assessment.likely_base_theme or 'n/a'})"
    )
    if audit.assessment.exposed_theme_name:
        print(f"Exposed theme name: {audit.assessment.exposed_theme_name}")
    if audit.assessment.rationale:
        print(f"Rationale: {audit.assessment.rationale}")
    print("Top candidates:")
    if audit.candidate_themes:
        for candidate in audit.candidate_themes[:5]:
            print(f"- {candidate.name}: {candidate.score}")
    else:
        print("- No theme candidates matched the current catalog.")

    print("Starter lineage:")
    if audit.lineage_themes:
        for candidate in audit.lineage_themes[:5]:
            print(f"- {candidate.name}: {candidate.score}")
    else:
        print("- No starter theme lineage matched the current catalog.")

    if audit.clues:
        print("Evidence:")
        for clue in audit.clues[:10]:
            print(f"- [{clue.kind}] {clue.value} ({clue.reason})")

    if ai_summary:
        print("AI summary:")
        print(ai_summary)
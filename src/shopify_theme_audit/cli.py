from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ai import summarize_audit
from .benchmark import benchmark_cases_by_slug, run_benchmarks
from .config import DEFAULT_CONFIG_PATH, initialize_config, load_config
from .detector import audit_storefront
from .exporter import export_fixture


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "audit": _handle_audit,
        "init-config": _handle_init_config,
        "export-fixture": _handle_export_fixture,
        "benchmark": _handle_benchmark,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


def _handle_audit(args) -> int:
    audit = audit_storefront(args.url)
    ai_summary = _load_ai_summary(args, audit)

    if args.format == "json":
        payload = audit.to_dict()
        if ai_summary:
            payload["ai_summary"] = ai_summary
        print(json.dumps(payload, indent=2))
    else:
        _print_human(audit, ai_summary)
    return 0


def _handle_init_config(args) -> int:
    path = initialize_config(args.path)
    print(f"Created config at {path}")
    return 0


def _handle_export_fixture(args) -> int:
    path = export_fixture(args.url, args.output)
    print(f"Wrote fixture bundle to {path}")
    return 0


def _handle_benchmark(args) -> int:
    cases = benchmark_cases_by_slug(set(args.case) if args.case else None)
    results = run_benchmarks(cases)
    failed = any(not result.passed for result in results)
    if args.format == "json":
        print(json.dumps([result.to_dict() for result in results], indent=2))
    else:
        _print_benchmarks(results)
    return 1 if failed else 0


def _load_ai_summary(args, audit) -> str | None:
    if not args.with_ai:
        return None
    config = load_config(args.config)
    provider = config.get_provider(args.provider)
    return summarize_audit(audit, provider)


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

    benchmark_parser = subparsers.add_parser("benchmark", help="Run built-in live validation benchmarks")
    benchmark_parser.add_argument("--case", action="append")
    benchmark_parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def _print_human(audit, ai_summary: str | None) -> None:
    cross_reference = audit.asset_cross_reference
    print(f"URL: {audit.url}")
    print(f"Final URL: {audit.final_url}")
    print(f"Status: {audit.status_code}")
    print(f"Shopify detected: {'yes' if audit.shopify_detected else 'no'}")
    _print_assessment(audit)
    _print_candidate_block("Top candidates:", audit.candidate_themes, "No theme candidates matched the current catalog.")
    _print_candidate_block("Starter lineage:", audit.lineage_themes, "No starter theme lineage matched the current catalog.")
    _print_lineage_diagnostics(audit)
    _print_evidence(audit)
    _print_cross_reference(cross_reference)

    if ai_summary:
        print("AI summary:")
        print(ai_summary)


def _print_assessment(audit) -> None:
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


def _print_candidate_block(title: str, candidates, empty_message: str) -> None:
    print(title)
    if candidates:
        for candidate in candidates[:5]:
            print(f"- {candidate.name}: {candidate.score}")
        return
    print(f"- {empty_message}")


def _print_evidence(audit) -> None:
    if not audit.clues:
        return
    print("Evidence:")
    for clue in audit.clues[:10]:
        print(f"- [{clue.kind}] {clue.value} ({clue.reason})")


def _print_cross_reference(cross_reference) -> None:
    print("Cross-reference:")
    print(f"- Asset count: {cross_reference.asset_count}")
    _print_optional_line("Shared stems", cross_reference.shared_filename_stems)
    _print_optional_line("Shared prefixes", cross_reference.shared_filename_prefixes)
    _print_optional_line("Repeated filename tokens", cross_reference.filename_tokens)
    _print_optional_line("Custom namespaces", cross_reference.custom_namespaces)
    if cross_reference.theme_asset_ids:
        print(f"- Theme asset ids: {', '.join(cross_reference.theme_asset_ids)}")
    if cross_reference.extension_assets:
        print(f"- Extension assets: {len(cross_reference.extension_assets)}")
    if cross_reference.app_assets:
        print(f"- App assets: {len(cross_reference.app_assets)}")


def _print_lineage_diagnostics(audit) -> None:
    if not audit.lineage_diagnostics:
        return
    print("Lineage diagnostics:")
    for diagnostic in audit.lineage_diagnostics[:5]:
        strong = ", ".join(diagnostic.strong_matches) or "none"
        weak = ", ".join(diagnostic.weak_matches) or "none"
        qualified = "yes" if diagnostic.qualified else "no"
        print(f"- {diagnostic.theme_name}: qualified={qualified}, strong=[{strong}], weak=[{weak}], score={diagnostic.score}")


def _print_optional_line(label: str, values: list[str]) -> None:
    if values:
        print(f"- {label}: {', '.join(values[:10])}")


def _print_benchmarks(results) -> None:
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.slug}")
        print(
            f"- classification: {result.audit.assessment.classification}"
            f" | base: {result.audit.assessment.likely_base_theme or 'n/a'}"
            f" | top candidate: {result.audit.candidate_themes[0].name if result.audit.candidate_themes else 'n/a'}"
        )
        if result.failures:
            for failure in result.failures:
                print(f"- {failure}")
from shopify_theme_audit.benchmark import BenchmarkCase, benchmark_cases_by_slug, run_benchmarks
from shopify_theme_audit.models import AssetCrossReference, StorefrontAudit, ThemeAssessment


def test_benchmark_filter_selects_known_cases() -> None:
    cases = benchmark_cases_by_slug({"official-dawn", "phaidon-custom"})

    assert {case.slug for case in cases} == {"official-dawn", "phaidon-custom"}


def test_benchmark_runner_evaluates_expected_and_forbidden_bases() -> None:
    cases = (
        BenchmarkCase(
            slug="custom-case",
            url="https://example.com",
            expected_shopify=True,
            expected_classifications=("shopify-custom",),
            forbidden_base_themes=("Dawn",),
        ),
    )

    def audit_func(_url: str) -> StorefrontAudit:
        return StorefrontAudit(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            shopify_detected=True,
            clues=[],
            candidate_themes=[],
            lineage_themes=[],
            lineage_diagnostics=[],
            assessment=ThemeAssessment(
                classification="shopify-custom",
                confidence=70,
                customness_score=80,
            ),
            raw_signals={},
            asset_cross_reference=AssetCrossReference(asset_count=0),
        )

    results = run_benchmarks(cases, audit_func=audit_func)

    assert results[0].passed is True
    assert results[0].failures == []
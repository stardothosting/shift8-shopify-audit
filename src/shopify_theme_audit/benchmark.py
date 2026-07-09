from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .detector import audit_storefront
from .models import StorefrontAudit


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    slug: str
    url: str
    expected_shopify: bool
    expected_classifications: tuple[str, ...] = ()
    expected_base_themes: tuple[str, ...] = ()
    forbidden_base_themes: tuple[str, ...] = ()
    expected_candidate_names: tuple[str, ...] = ()


@dataclass(slots=True)
class BenchmarkResult:
    slug: str
    passed: bool
    failures: list[str]
    audit: StorefrontAudit

    def to_dict(self) -> dict[str, object]:
        return {
            "slug": self.slug,
            "passed": self.passed,
            "failures": self.failures,
            "audit": self.audit.to_dict(),
        }


BUILTIN_BENCHMARKS: tuple[BenchmarkCase, ...] = (
    BenchmarkCase(
        slug="official-dawn",
        url="https://theme-dawn-demo.myshopify.com",
        expected_shopify=True,
        expected_classifications=("known-theme", "catalog-match"),
        expected_base_themes=("Dawn",),
        expected_candidate_names=("Dawn",),
    ),
    BenchmarkCase(
        slug="official-prestige",
        url="https://prestige-theme-allure.myshopify.com",
        expected_shopify=True,
        expected_classifications=("known-theme", "catalog-match"),
        expected_base_themes=("Prestige",),
        expected_candidate_names=("Prestige",),
    ),
    BenchmarkCase(
        slug="phaidon-custom",
        url="https://www.phaidon.com/en-ca",
        expected_shopify=True,
        expected_classifications=("shopify-custom", "custom-derived", "custom-unknown"),
        forbidden_base_themes=("Dawn", "Prestige"),
    ),
)


def run_benchmarks(
    cases: tuple[BenchmarkCase, ...] | None = None,
    audit_func: Callable[[str], StorefrontAudit] = audit_storefront,
) -> list[BenchmarkResult]:
    selected_cases = cases or BUILTIN_BENCHMARKS
    return [_evaluate_case(case, audit_func(case.url)) for case in selected_cases]


def benchmark_cases_by_slug(slugs: set[str] | None = None) -> tuple[BenchmarkCase, ...]:
    if not slugs:
        return BUILTIN_BENCHMARKS
    return tuple(case for case in BUILTIN_BENCHMARKS if case.slug in slugs)


def _evaluate_case(case: BenchmarkCase, audit: StorefrontAudit) -> BenchmarkResult:
    failures: list[str] = []
    candidate_names = {candidate.name for candidate in audit.candidate_themes[:5]}
    classification = audit.assessment.classification
    base_theme = audit.assessment.likely_base_theme

    _append_shopify_failure(failures, case, audit.shopify_detected)
    _append_classification_failure(failures, case, classification)
    _append_expected_base_failure(failures, case, base_theme)
    _append_forbidden_base_failure(failures, case, base_theme)
    _append_candidate_failure(failures, case, candidate_names)

    return BenchmarkResult(
        slug=case.slug,
        passed=not failures,
        failures=failures,
        audit=audit,
    )


def _append_shopify_failure(failures: list[str], case: BenchmarkCase, detected: bool) -> None:
    if detected is not case.expected_shopify:
        failures.append(f"expected shopify_detected={case.expected_shopify} but got {detected}")


def _append_classification_failure(failures: list[str], case: BenchmarkCase, classification: str) -> None:
    if case.expected_classifications and classification not in case.expected_classifications:
        failures.append(f"expected classification in {case.expected_classifications} but got {classification}")


def _append_expected_base_failure(failures: list[str], case: BenchmarkCase, base_theme: str | None) -> None:
    if case.expected_base_themes and base_theme not in case.expected_base_themes:
        failures.append(f"expected base theme in {case.expected_base_themes} but got {base_theme}")


def _append_forbidden_base_failure(failures: list[str], case: BenchmarkCase, base_theme: str | None) -> None:
    if case.forbidden_base_themes and base_theme in case.forbidden_base_themes:
        failures.append(f"forbidden base theme matched: {base_theme}")


def _append_candidate_failure(failures: list[str], case: BenchmarkCase, candidate_names: set[str]) -> None:
    if case.expected_candidate_names and not candidate_names.intersection(case.expected_candidate_names):
        failures.append(
            f"expected one of candidate names {case.expected_candidate_names} in top candidates but got {sorted(candidate_names)}"
        )
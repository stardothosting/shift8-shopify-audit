from __future__ import annotations

from .asset_probe import build_asset_probe_signals, select_probe_asset_urls
from .catalog import STARTER_THEME_CATALOG, THEME_CATALOG
from .fetcher import fetch_html, fetch_text_assets
from .fingerprints import extract_signals
from .models import CandidateTheme, Evidence, StorefrontAudit, ThemeAssessment


def audit_storefront(url: str) -> StorefrontAudit:
    response = fetch_html(url)
    return audit_storefront_payload(
        url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        html=response.text,
    )


def audit_storefront_payload(
    url: str, final_url: str, status_code: int, html: str, asset_bodies: dict[str, str] | None = None
) -> StorefrontAudit:
    signals, clues, shopify_detected = extract_signals(html, final_url)
    if shopify_detected:
        resolved_asset_bodies = asset_bodies
        if resolved_asset_bodies is None:
            probe_urls = select_probe_asset_urls(signals)
            resolved_asset_bodies = fetch_text_assets(probe_urls)
        asset_signals, asset_clues = build_asset_probe_signals(resolved_asset_bodies, (THEME_CATALOG, STARTER_THEME_CATALOG))
        _merge_signals(signals, asset_signals)
        clues.extend(asset_clues)

    candidate_themes = score_candidates(signals, clues)
    lineage_themes = score_lineages(signals, clues)
    assessment = assess_theme_identity(shopify_detected, clues, candidate_themes, lineage_themes)
    return StorefrontAudit(
        url=url,
        final_url=final_url,
        status_code=status_code,
        shopify_detected=shopify_detected,
        clues=clues,
        candidate_themes=candidate_themes,
        lineage_themes=lineage_themes,
        assessment=assessment,
        raw_signals=signals,
    )


def score_candidates(signals: dict[str, list[str]], clues: list[Evidence]) -> list[CandidateTheme]:
    return _score_catalog(signals, clues, THEME_CATALOG, exact_name_bonus=20)


def score_lineages(signals: dict[str, list[str]], clues: list[Evidence]) -> list[CandidateTheme]:
    return _score_catalog(signals, clues, STARTER_THEME_CATALOG, exact_name_bonus=10)


def assess_theme_identity(
    shopify_detected: bool,
    clues: list[Evidence],
    candidate_themes: list[CandidateTheme],
    lineage_themes: list[CandidateTheme],
) -> ThemeAssessment:
    exposed_theme_name = next((clue.value for clue in clues if clue.kind == "theme_name"), None)
    known_theme = candidate_themes[0] if candidate_themes else None
    starter_lineage = lineage_themes[0] if lineage_themes else None

    for builder in (
        lambda: _build_exact_match_assessment(exposed_theme_name, known_theme),
        lambda: _build_custom_derived_assessment(exposed_theme_name, starter_lineage),
        lambda: _build_catalog_match_assessment(exposed_theme_name, known_theme),
        lambda: _build_starter_match_assessment(exposed_theme_name, starter_lineage),
    ):
        assessment = builder()
        if assessment is not None:
            return assessment

    if exposed_theme_name is not None:
        return _build_custom_unknown_assessment(exposed_theme_name)

    fallback_builder = _build_unclassified_shopify_assessment if shopify_detected else _build_non_shopify_assessment
    return fallback_builder()


def _score_catalog(
    signals: dict[str, list[str]], clues: list[Evidence], catalog: dict[str, dict[str, list[str] | int]], exact_name_bonus: int
) -> list[CandidateTheme]:
    haystacks = [
        *signals.get("script_urls", []),
        *signals.get("stylesheet_urls", []),
        *signals.get("asset_paths", []),
        *signals.get("asset_filenames", []),
        *signals.get("asset_content_tokens", []),
        *signals.get("classes", []),
        *signals.get("attributes", []),
        *signals.get("theme_names", []),
        *signals.get("meta", []),
    ]
    searchable = "\n".join(haystacks).lower()
    exact_theme_names = {clue.value.lower(): clue for clue in clues if clue.kind == "theme_name"}
    matches: list[CandidateTheme] = []

    for theme_name, rule in catalog.items():
        matched_evidence: list[Evidence] = []
        score = 0
        if theme_name.lower() in exact_theme_names:
            matched_evidence.append(exact_theme_names[theme_name.lower()])
            score += exact_name_bonus

        rule_weight = int(rule["weight"])
        for token in rule["tokens"]:
            if token.lower() in searchable:
                matched_evidence.append(
                    Evidence(
                        kind="fingerprint",
                        source="catalog",
                        value=token,
                        weight=rule_weight,
                        reason=f"Matched known fingerprint token for {theme_name}.",
                    )
                )
                score += rule_weight

        if score:
            matches.append(
                CandidateTheme(
                    name=theme_name,
                    score=score,
                    matched_evidence=matched_evidence,
                )
            )

    return sorted(matches, key=lambda item: item.score, reverse=True)


def _build_exact_match_assessment(exposed_theme_name: str | None, known_theme: CandidateTheme | None) -> ThemeAssessment | None:
    if not known_theme or not exposed_theme_name or known_theme.name.lower() != exposed_theme_name.lower():
        return None
    confidence = min(100, 55 + known_theme.score)
    return ThemeAssessment(
        classification="known-theme",
        confidence=confidence,
        customness_score=10,
        exposed_theme_name=exposed_theme_name,
        likely_base_theme=known_theme.name,
        rationale="The storefront exposes a theme name that matches the strongest known theme fingerprint.",
        matched_evidence=known_theme.matched_evidence,
    )


def _build_custom_derived_assessment(
    exposed_theme_name: str | None, starter_lineage: CandidateTheme | None
) -> ThemeAssessment | None:
    if not starter_lineage or not exposed_theme_name or starter_lineage.name.lower() == exposed_theme_name.lower():
        return None
    confidence = min(95, 35 + starter_lineage.score)
    return ThemeAssessment(
        classification="custom-derived",
        confidence=confidence,
        customness_score=85,
        exposed_theme_name=exposed_theme_name,
        likely_base_theme=starter_lineage.name,
        rationale="The storefront exposes a custom theme name, but its asset and markup signatures strongly resemble a known starter theme.",
        matched_evidence=starter_lineage.matched_evidence,
    )


def _build_catalog_match_assessment(
    exposed_theme_name: str | None, known_theme: CandidateTheme | None
) -> ThemeAssessment | None:
    if not known_theme:
        return None
    confidence = min(90, 30 + known_theme.score)
    return ThemeAssessment(
        classification="catalog-match",
        confidence=confidence,
        customness_score=20,
        exposed_theme_name=exposed_theme_name,
        likely_base_theme=known_theme.name,
        rationale="The storefront does not expose a definitive theme name, but the strongest fingerprint match maps to a known theme.",
        matched_evidence=known_theme.matched_evidence,
    )


def _build_starter_match_assessment(
    exposed_theme_name: str | None, starter_lineage: CandidateTheme | None
) -> ThemeAssessment | None:
    if not starter_lineage:
        return None
    confidence = min(85, 30 + starter_lineage.score)
    return ThemeAssessment(
        classification="starter-derived",
        confidence=confidence,
        customness_score=70,
        exposed_theme_name=exposed_theme_name,
        likely_base_theme=starter_lineage.name,
        rationale="The storefront looks customized, but the strongest static signatures point to a starter theme lineage.",
        matched_evidence=starter_lineage.matched_evidence,
    )


def _build_custom_unknown_assessment(exposed_theme_name: str) -> ThemeAssessment:
    return ThemeAssessment(
        classification="custom-unknown",
        confidence=40,
        customness_score=90,
        exposed_theme_name=exposed_theme_name,
        rationale="The storefront exposes a theme name, but it does not match the current signature catalogs.",
    )


def _build_unclassified_shopify_assessment() -> ThemeAssessment:
    return ThemeAssessment(
        classification="shopify-unclassified",
        confidence=25,
        customness_score=55,
        rationale="The storefront appears to be on Shopify, but there are not enough known signatures yet to classify its theme lineage.",
    )


def _build_non_shopify_assessment() -> ThemeAssessment:
    return ThemeAssessment(
        classification="non-shopify-or-undetected",
        confidence=0,
        customness_score=0,
        rationale="The current signals do not confidently identify Shopify storefront infrastructure.",
    )


def _merge_signals(signals: dict[str, list[str]], additional_signals: dict[str, list[str]]) -> None:
    for key, values in additional_signals.items():
        target = signals.setdefault(key, [])
        existing = set(target)
        for value in values:
            if value not in existing:
                target.append(value)
                existing.add(value)
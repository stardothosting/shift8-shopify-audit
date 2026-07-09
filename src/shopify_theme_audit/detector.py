from __future__ import annotations

from .asset_probe import build_asset_probe_signals, select_probe_asset_urls
from .catalog import STARTER_THEME_CATALOG, THEME_CATALOG
from .fetcher import fetch_html, fetch_text_assets
from .cross_reference import analyze_asset_cross_reference
from .fingerprints import extract_signals
from .models import AssetCrossReference, CandidateTheme, Evidence, LineageDiagnostic, StorefrontAudit, ThemeAssessment


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

    asset_cross_reference = analyze_asset_cross_reference(signals)

    candidate_themes = score_candidates(signals, clues)
    lineage_themes, lineage_diagnostics = score_lineages(signals, clues)
    assessment = assess_theme_identity(shopify_detected, clues, candidate_themes, lineage_themes, asset_cross_reference)
    return StorefrontAudit(
        url=url,
        final_url=final_url,
        status_code=status_code,
        shopify_detected=shopify_detected,
        clues=clues,
        candidate_themes=candidate_themes,
        lineage_themes=lineage_themes,
        lineage_diagnostics=lineage_diagnostics,
        assessment=assessment,
        asset_cross_reference=asset_cross_reference,
        raw_signals=signals,
    )


def score_candidates(signals: dict[str, list[str]], clues: list[Evidence]) -> list[CandidateTheme]:
    return _score_catalog(signals, clues, THEME_CATALOG, exact_name_bonus=20)


def score_lineages(signals: dict[str, list[str]], clues: list[Evidence]) -> tuple[list[CandidateTheme], list[LineageDiagnostic]]:
    return _score_lineages(signals, clues, STARTER_THEME_CATALOG, exact_name_bonus=10)


def assess_theme_identity(
    shopify_detected: bool,
    clues: list[Evidence],
    candidate_themes: list[CandidateTheme],
    lineage_themes: list[CandidateTheme],
    asset_cross_reference: AssetCrossReference,
) -> ThemeAssessment:
    exposed_theme_name = next((clue.value for clue in clues if clue.kind == "theme_name"), None)
    known_theme = candidate_themes[0] if candidate_themes else None
    starter_lineage = lineage_themes[0] if lineage_themes else None

    custom_namespace_assessment = _build_custom_namespace_assessment(
        shopify_detected, exposed_theme_name, known_theme, starter_lineage, asset_cross_reference
    )
    if custom_namespace_assessment is not None:
        return custom_namespace_assessment

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
    searchable = _searchable_signals(signals)
    exact_theme_names = {clue.value.lower(): clue for clue in clues if clue.kind == "theme_name"}
    matches: list[CandidateTheme] = []

    for theme_name, rule in catalog.items():
        candidate = _score_known_theme_candidate(theme_name, rule, searchable, exact_theme_names, exact_name_bonus)
        if candidate is not None:
            matches.append(candidate)

    return sorted(matches, key=lambda item: item.score, reverse=True)


def _score_lineages(
    signals: dict[str, list[str]], clues: list[Evidence], catalog: dict[str, dict[str, list[str] | int]], exact_name_bonus: int
) -> tuple[list[CandidateTheme], list[LineageDiagnostic]]:
    searchable = _searchable_signals(signals)
    exact_theme_names = {clue.value.lower(): clue for clue in clues if clue.kind == "theme_name"}
    candidates: list[CandidateTheme] = []
    diagnostics: list[LineageDiagnostic] = []

    for theme_name, rule in catalog.items():
        diagnostic = _build_lineage_diagnostic(theme_name, rule, searchable, exact_theme_names, exact_name_bonus)
        diagnostics.append(diagnostic)
        if not diagnostic.qualified:
            continue

        candidates.append(
            CandidateTheme(
                name=theme_name,
                score=diagnostic.score,
                matched_evidence=_matched_lineage_evidence(theme_name, rule, diagnostic, exact_theme_names),
            )
        )

    candidates.sort(key=lambda item: item.score, reverse=True)
    diagnostics.sort(key=lambda item: item.score, reverse=True)
    return candidates, diagnostics


def _catalog_token_groups(rule: dict[str, list[str] | int]) -> tuple[list[str], list[str]]:
    strong_tokens = rule.get("strong_tokens")
    weak_tokens = rule.get("weak_tokens")
    direct_tokens = rule.get("tokens")
    if isinstance(strong_tokens, list) or isinstance(weak_tokens, list):
        return list(strong_tokens or []), list(weak_tokens or [])
    return list(direct_tokens or []), []


def _searchable_signals(signals: dict[str, list[str]]) -> str:
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
    return "\n".join(haystacks).lower()


def _score_known_theme_candidate(
    theme_name: str,
    rule: dict[str, list[str] | int],
    searchable: str,
    exact_theme_names: dict[str, Evidence],
    exact_name_bonus: int,
) -> CandidateTheme | None:
    score, matched_evidence = _known_theme_score_parts(theme_name, rule, searchable, exact_theme_names, exact_name_bonus)
    if not score:
        return None
    return CandidateTheme(name=theme_name, score=score, matched_evidence=matched_evidence)


def _known_theme_score_parts(
    theme_name: str,
    rule: dict[str, list[str] | int],
    searchable: str,
    exact_theme_names: dict[str, Evidence],
    exact_name_bonus: int,
) -> tuple[int, list[Evidence]]:
    matched_evidence: list[Evidence] = []
    score = 0
    strong_tokens, weak_tokens = _catalog_token_groups(rule)
    has_exact_name = theme_name.lower() in exact_theme_names
    if has_exact_name:
        matched_evidence.append(exact_theme_names[theme_name.lower()])
        score += exact_name_bonus

    rule_weight = int(rule["weight"])
    strong_matches = _matching_tokens(strong_tokens, searchable)
    weak_matches = _matching_tokens(weak_tokens, searchable)
    score += _append_token_evidence(matched_evidence, theme_name, strong_matches, rule_weight, "known-theme")

    if score or has_exact_name:
        score += _append_token_evidence(matched_evidence, theme_name, weak_matches, _weak_weight(rule), "known-theme", strength="weak")
    return score, matched_evidence


def _append_token_evidence(
    matched_evidence: list[Evidence],
    theme_name: str,
    matches: list[str],
    weight: int,
    label: str,
    strength: str = "strong",
) -> int:
    for token in matches:
        matched_evidence.append(
            Evidence(
                kind="fingerprint",
                source="catalog",
                value=token,
                weight=weight,
                reason=f"Matched {strength} {label} fingerprint token for {theme_name}.",
            )
        )
    return len(matches) * weight


def _build_lineage_diagnostic(
    theme_name: str,
    rule: dict[str, list[str] | int],
    searchable: str,
    exact_theme_names: dict[str, Evidence],
    exact_name_bonus: int,
) -> LineageDiagnostic:
    strong_tokens, weak_tokens = _catalog_token_groups(rule)
    strong_matches = _matching_tokens(strong_tokens, searchable)
    weak_matches = _matching_tokens(weak_tokens, searchable)
    has_exact_name = theme_name.lower() in exact_theme_names
    qualified = has_exact_name or _qualifies_lineage(rule, strong_matches, weak_matches)
    score = (exact_name_bonus if has_exact_name else 0) + len(strong_matches) * int(rule["weight"]) + len(weak_matches) * _weak_weight(rule)
    return LineageDiagnostic(
        theme_name=theme_name,
        strong_matches=strong_matches,
        weak_matches=weak_matches,
        qualified=qualified,
        score=score,
    )


def _matched_lineage_evidence(
    theme_name: str,
    rule: dict[str, list[str] | int],
    diagnostic: LineageDiagnostic,
    exact_theme_names: dict[str, Evidence],
) -> list[Evidence]:
    matched_evidence: list[Evidence] = []
    if theme_name.lower() in exact_theme_names:
        matched_evidence.append(exact_theme_names[theme_name.lower()])
    _append_token_evidence(matched_evidence, theme_name, diagnostic.strong_matches, int(rule["weight"]), "starter-theme")
    _append_token_evidence(matched_evidence, theme_name, diagnostic.weak_matches, _weak_weight(rule), "starter-theme", strength="weak")
    return matched_evidence


def _matching_tokens(tokens: list[str], searchable: str) -> list[str]:
    return [token for token in tokens if token.lower() in searchable]


def _weak_weight(rule: dict[str, list[str] | int]) -> int:
    explicit = rule.get("weak_weight")
    if isinstance(explicit, int):
        return explicit
    return max(1, int(rule["weight"]) // 2)


def _qualifies_lineage(rule: dict[str, list[str] | int], strong_matches: list[str], weak_matches: list[str]) -> bool:
    min_strong = int(rule.get("min_strong", 1))
    min_weak = int(rule.get("min_weak", 0))
    if len(strong_matches) >= max(2, min_strong):
        return True
    return len(strong_matches) >= min_strong and len(weak_matches) >= min_weak and len(strong_matches) > 0


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


def _build_custom_namespace_assessment(
    shopify_detected: bool,
    exposed_theme_name: str | None,
    known_theme: CandidateTheme | None,
    starter_lineage: CandidateTheme | None,
    asset_cross_reference: AssetCrossReference,
) -> ThemeAssessment | None:
    if not shopify_detected or not asset_cross_reference.custom_namespaces:
        return None
    if not _is_weak_match(known_theme) and not _is_weak_match(starter_lineage):
        return None

    namespace_label = ", ".join(asset_cross_reference.custom_namespaces[:3])
    return ThemeAssessment(
        classification="shopify-custom",
        confidence=68,
        customness_score=88,
        exposed_theme_name=exposed_theme_name,
        rationale=(
            "The storefront has a strong internal asset and class namespace "
            f"({namespace_label}), while the current theme-library matches are weak and generic."
        ),
    )


def _is_weak_match(candidate: CandidateTheme | None) -> bool:
    if candidate is None:
        return True
    if candidate.score >= 12:
        return False
    if len(candidate.matched_evidence) > 1:
        return False
    if not candidate.matched_evidence:
        return True
    return candidate.matched_evidence[0].value in {"predictive-search", "quick-add__submit", "price__container", "global.js"}


def _merge_signals(signals: dict[str, list[str]], additional_signals: dict[str, list[str]]) -> None:
    for key, values in additional_signals.items():
        target = signals.setdefault(key, [])
        existing = set(target)
        for value in values:
            if value not in existing:
                target.append(value)
                existing.add(value)
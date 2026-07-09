from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .models import Evidence


PROBE_FILE_HINTS = (
    "global.js",
    "theme.js",
    "theme.min.js",
    "base.css",
    "theme.css",
    "component-",
    "section-",
    "sections-",
    "card-product",
    "quick-add",
    "predictive-search",
)


def select_probe_asset_urls(signals: dict[str, list[str]], limit: int = 6) -> list[str]:
    ranked_urls: list[tuple[int, str]] = []
    seen: set[str] = set()
    for bucket_name in ("script_urls", "stylesheet_urls"):
        for url in signals.get(bucket_name, []):
            if url in seen:
                continue
            seen.add(url)
            ranked_urls.append((_score_probe_url(url), url))

    ranked_urls.sort(key=lambda item: item[0], reverse=True)
    return [url for score, url in ranked_urls if score > 0][:limit]


def build_asset_probe_signals(
    asset_bodies: dict[str, str], catalogs: Iterable[dict[str, dict[str, list[str] | int]]]
) -> tuple[dict[str, list[str]], list[Evidence]]:
    signals: dict[str, list[str]] = defaultdict(list)
    clues: list[Evidence] = []
    catalog_tokens = _catalog_tokens(catalogs)

    for asset_url, body in asset_bodies.items():
        signals["probed_asset_urls"].append(asset_url)
        lower_body = body.lower()
        for token in catalog_tokens:
            if token in lower_body:
                signals["asset_content_tokens"].append(token)
                clues.append(
                    Evidence(
                        kind="asset_probe",
                        source="asset_content",
                        value=token,
                        weight=6,
                        reason="Fetched asset content contains a known theme or starter-theme token.",
                    )
                )

    deduped_signals = {name: sorted(set(values)) for name, values in signals.items()}
    return deduped_signals, _dedupe_evidence(clues)


def _score_probe_url(url: str) -> int:
    lowered = url.lower()
    score = 0
    for hint in PROBE_FILE_HINTS:
        if hint in lowered:
            score += 10
    return score


def _catalog_tokens(catalogs: Iterable[dict[str, dict[str, list[str] | int]]]) -> set[str]:
    tokens: set[str] = set()
    for catalog in catalogs:
        for rule in catalog.values():
            for token in _rule_tokens(rule):
                tokens.add(token.lower())
    return tokens


def _rule_tokens(rule: dict[str, list[str] | int]) -> list[str]:
    strong_tokens = rule.get("strong_tokens")
    weak_tokens = rule.get("weak_tokens")
    direct_tokens = rule.get("tokens")
    tokens: list[str] = []
    if isinstance(strong_tokens, list):
        tokens.extend(strong_tokens)
    if isinstance(weak_tokens, list):
        tokens.extend(weak_tokens)
    if isinstance(direct_tokens, list):
        tokens.extend(direct_tokens)
    return tokens


def _dedupe_evidence(clues: list[Evidence]) -> list[Evidence]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[Evidence] = []
    for clue in clues:
        marker = (clue.kind, clue.source, clue.value, clue.reason)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(clue)
    return result
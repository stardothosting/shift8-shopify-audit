from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import urljoin
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .models import Evidence


SHOPIFY_PATTERNS = {
    "shopify_cdn": re.compile(r"cdn\.shopify\.com|cdn/shop/"),
    "theme_asset_id": re.compile(r"/cdn/shop/t/(\d+)/assets/"),
    "shopify_theme_obj": re.compile(r"Shopify\.theme\s*=\s*\{.*?[\"']?name[\"']?\s*:\s*[\"']([^\"']+)[\"']", re.IGNORECASE | re.DOTALL),
    "shopify_theme_name": re.compile(r"Shopify\.theme\.name\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE),
}


def extract_signals(html: str, base_url: str) -> tuple[dict[str, list[str]], list[Evidence], bool]:
    soup = BeautifulSoup(html, "html.parser")
    signals: dict[str, list[str]] = defaultdict(list)
    for bucket_name in (
        "script_urls",
        "stylesheet_urls",
        "asset_paths",
        "asset_filenames",
        "theme_asset_ids",
        "classes",
        "attributes",
        "theme_names",
        "meta",
        "asset_content_tokens",
        "probed_asset_urls",
    ):
        signals.setdefault(bucket_name, [])
    clues: list[Evidence] = []

    _collect_script_signals(soup, base_url, signals, clues)
    _collect_stylesheet_signals(soup, base_url, signals, clues)
    _collect_dom_signals(soup, signals)
    _collect_meta_signals(soup, signals, clues)

    shopify_detected = any(clue.kind == "platform" for clue in clues)
    deduped_signals = {key: sorted(set(values)) for key, values in signals.items()}
    deduped_clues = _dedupe_evidence(clues)
    return deduped_signals, deduped_clues, shopify_detected


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


def _append_asset_markers(signals: dict[str, list[str]], absolute_url: str) -> None:
    path = urlparse(absolute_url).path
    if not path:
        return
    signals["asset_paths"].append(path)
    file_name = path.rsplit("/", 1)[-1]
    if file_name:
        signals["asset_filenames"].append(file_name)


def _collect_script_signals(
    soup: BeautifulSoup, base_url: str, signals: dict[str, list[str]], clues: list[Evidence]
) -> None:
    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            _collect_script_source(urljoin(base_url, src), signals, clues)

        script_text = script.string or script.get_text(" ", strip=True)
        if script_text:
            _collect_theme_names_from_script(script_text, signals, clues)


def _collect_script_source(absolute_src: str, signals: dict[str, list[str]], clues: list[Evidence]) -> None:
    signals["script_urls"].append(absolute_src)
    _append_asset_markers(signals, absolute_src)
    if SHOPIFY_PATTERNS["shopify_cdn"].search(absolute_src):
        clues.append(
            Evidence(
                kind="platform",
                source="script",
                value=absolute_src,
                weight=7,
                reason="Script URL points to Shopify CDN infrastructure.",
            )
        )


def _collect_theme_names_from_script(script_text: str, signals: dict[str, list[str]], clues: list[Evidence]) -> None:
    for pattern_name in ("shopify_theme_obj", "shopify_theme_name"):
        for match in SHOPIFY_PATTERNS[pattern_name].finditer(script_text):
            theme_name = match.group(1).strip()
            if _looks_like_theme_noise(theme_name, script_text):
                continue
            signals["theme_names"].append(theme_name)
            clues.append(
                Evidence(
                    kind="theme_name",
                    source="script_text",
                    value=theme_name,
                    weight=10,
                    reason="Theme name exposed in storefront JavaScript.",
                )
            )


def _collect_stylesheet_signals(
    soup: BeautifulSoup, base_url: str, signals: dict[str, list[str]], clues: list[Evidence]
) -> None:
    for link in soup.find_all("link"):
        href = link.get("href")
        if not href:
            continue
        absolute_href = urljoin(base_url, href)
        signals["stylesheet_urls"].append(absolute_href)
        _append_asset_markers(signals, absolute_href)
        _collect_stylesheet_clues(absolute_href, signals, clues)


def _collect_stylesheet_clues(absolute_href: str, signals: dict[str, list[str]], clues: list[Evidence]) -> None:
    if SHOPIFY_PATTERNS["shopify_cdn"].search(absolute_href):
        clues.append(
            Evidence(
                kind="platform",
                source="stylesheet",
                value=absolute_href,
                weight=7,
                reason="Stylesheet URL points to Shopify CDN infrastructure.",
            )
        )

    asset_match = SHOPIFY_PATTERNS["theme_asset_id"].search(absolute_href)
    if asset_match:
        theme_id = asset_match.group(1)
        signals["theme_asset_ids"].append(theme_id)
        clues.append(
            Evidence(
                kind="theme_asset_id",
                source="stylesheet",
                value=theme_id,
                weight=5,
                reason="Theme asset path exposes a Shopify theme asset identifier.",
            )
        )


def _collect_dom_signals(soup: BeautifulSoup, signals: dict[str, list[str]]) -> None:
    for tag in soup.find_all(True):
        classes = tag.get("class") or []
        for class_name in classes:
            signals["classes"].append(class_name)
        for attr_name in ("id", "data-section-id", "data-section-type", "data-template"):
            attr_value = tag.get(attr_name)
            if attr_value:
                signals["attributes"].append(f"{attr_name}={attr_value}")


def _collect_meta_signals(soup: BeautifulSoup, signals: dict[str, list[str]], clues: list[Evidence]) -> None:
    meta_generator = soup.find("meta", attrs={"name": "generator"})
    if not meta_generator or not meta_generator.get("content"):
        return
    content = meta_generator["content"]
    signals["meta"].append(content)
    if "shopify" in content.lower():
        clues.append(
            Evidence(
                kind="platform",
                source="meta",
                value=content,
                weight=8,
                reason="Generator metadata identifies Shopify.",
            )
        )


def _looks_like_theme_noise(theme_name: str, script_text: str) -> bool:
    lowered_name = theme_name.lower().strip()
    lowered_script = script_text.lower()
    if not lowered_name:
        return True
    if ".handle" in lowered_name or "shopify.theme" in lowered_name:
        return True
    if lowered_name in {"handle", "name", "theme", "shopify"}:
        return True
    if "shopify.theme.handle" in lowered_script and lowered_name in lowered_script:
        return True
    return False
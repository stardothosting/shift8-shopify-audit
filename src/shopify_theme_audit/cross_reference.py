from __future__ import annotations

from collections import Counter

from .models import AssetCrossReference


def analyze_asset_cross_reference(signals: dict[str, list[str]]) -> AssetCrossReference:
    asset_urls = [*signals.get("script_urls", []), *signals.get("stylesheet_urls", [])]
    filenames = signals.get("asset_filenames", [])
    class_names = signals.get("classes", [])
    stems = [_normalize_stem(filename) for filename in filenames if filename]
    shared_filename_stems = _shared_filename_stems(stems)
    shared_filename_prefixes = _shared_filename_prefixes(stems)
    filename_tokens = _filename_tokens(stems)
    custom_namespaces = _custom_namespaces(stems, class_names)

    return AssetCrossReference(
        asset_count=len(asset_urls),
        shared_filename_stems=shared_filename_stems,
        shared_filename_prefixes=shared_filename_prefixes,
        filename_tokens=filename_tokens,
        custom_namespaces=custom_namespaces,
        theme_asset_ids=sorted(set(signals.get("theme_asset_ids", []))),
        shopify_cloud_assets=_collect_assets(asset_urls, "cdn.shopify.com/shopifycloud/"),
        extension_assets=_collect_assets(asset_urls, "/extensions/"),
        app_assets=_collect_assets(asset_urls, "/apps/"),
    )


def _normalize_stem(filename: str) -> str:
    lower = filename.split("?", 1)[0].lower()
    if lower.endswith(".liquid"):
        lower = lower[: -len(".liquid")]
    if "." in lower:
        lower = lower.rsplit(".", 1)[0]
    if lower.endswith(".min"):
        lower = lower[: -len(".min")]
    return lower.strip()


def _stem_prefix(stem: str) -> str:
    for separator in ("-", "_", "."):
        if separator in stem:
            return stem.split(separator, 1)[0]
    return stem


def _stem_tokens(stem: str) -> list[str]:
    tokens: list[str] = []
    current = []
    for char in stem:
        if char.isalnum():
            current.append(char)
            continue
        if current:
            token = "".join(current)
            if len(token) >= 3 and not token.isdigit():
                tokens.append(token)
            current = []
    if current:
        token = "".join(current)
        if len(token) >= 3 and not token.isdigit():
            tokens.append(token)
    return tokens


def _file_namespace(stem: str) -> str | None:
    if stem.startswith("section-"):
        remainder = stem[len("section-") :]
        if "-" in remainder:
            namespace = remainder.split("-", 1)[0]
            return namespace if _is_namespace_candidate(namespace) else None
    if "-" in stem:
        namespace = stem.split("-", 1)[0]
        return namespace if _is_namespace_candidate(namespace) else None
    return None


def _class_namespace(class_name: str) -> str | None:
    for separator in ("-", "_"):
        if separator in class_name:
            namespace = class_name.split(separator, 1)[0].lower()
            return namespace if _is_namespace_candidate(namespace) else None
    return None


def _is_namespace_candidate(namespace: str) -> bool:
    return 2 <= len(namespace) <= 5 and namespace.isalpha()


def _collect_assets(asset_urls: list[str], needle: str) -> list[str]:
    return sorted([url for url in asset_urls if needle in url])


def _shared_filename_stems(stems: list[str]) -> list[str]:
    stem_counts = Counter(stem for stem in stems if stem)
    return sorted([stem for stem, count in stem_counts.items() if count > 1])


def _shared_filename_prefixes(stems: list[str]) -> list[str]:
    prefix_counts = Counter(prefix for stem in stems if (prefix := _stem_prefix(stem)))
    return sorted([prefix for prefix, count in prefix_counts.items() if count > 1 and prefix not in _STOP_PREFIXES])


def _filename_tokens(stems: list[str]) -> list[str]:
    token_counts = Counter(token for stem in stems for token in _stem_tokens(stem))
    return sorted([token for token, count in token_counts.items() if count > 1 and token not in _STOP_TOKENS])


def _custom_namespaces(stems: list[str], class_names: list[str]) -> list[str]:
    file_namespace_counts = Counter(namespace for stem in stems if (namespace := _file_namespace(stem)))
    class_namespace_counts = Counter(namespace for class_name in class_names if (namespace := _class_namespace(class_name)))
    return sorted(
        namespace
        for namespace, count in (file_namespace_counts & class_namespace_counts).items()
        if count >= 2 and namespace not in _STOP_NAMESPACES
    )


_STOP_PREFIXES = {"js", "css", "theme", "asset", "assets", "shopify", "storefront", "cdn"}
_STOP_TOKENS = {"shopify", "storefront", "assets", "asset", "theme", "js", "css", "min"}
_STOP_NAMESPACES = {"card", "cart", "icon", "text", "link", "grid", "form", "shop", "menu", "blog", "hero", "quick"}
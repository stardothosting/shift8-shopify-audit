from __future__ import annotations

import json
from pathlib import Path

from .asset_probe import select_probe_asset_urls
from .detector import audit_storefront_payload
from .fetcher import fetch_html, fetch_text_assets
from .fingerprints import extract_signals


def export_fixture(url: str, output_path: Path) -> Path:
    response = fetch_html(url)
    fixture_bundle = build_fixture_bundle(
        url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        html=response.text,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(fixture_bundle, indent=2), encoding="utf-8")
    return output_path


def build_fixture_bundle(
    url: str,
    final_url: str,
    status_code: int,
    html: str,
    asset_bodies: dict[str, str] | None = None,
) -> dict[str, object]:
    signals, _clues, shopify_detected = extract_signals(html, final_url)
    probe_urls = select_probe_asset_urls(signals) if shopify_detected else []
    resolved_asset_bodies = asset_bodies if asset_bodies is not None else fetch_text_assets(probe_urls)
    audit = audit_storefront_payload(
        url=url,
        final_url=final_url,
        status_code=status_code,
        html=html,
        asset_bodies=resolved_asset_bodies,
    )
    return {
        "url": url,
        "final_url": final_url,
        "status_code": status_code,
        "html": html,
        "selected_asset_urls": probe_urls,
        "asset_bodies": resolved_asset_bodies,
        "raw_signals": audit.raw_signals,
        "audit": audit.to_dict(),
    }
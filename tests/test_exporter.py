from __future__ import annotations

import json

import httpx

from shopify_theme_audit.exporter import build_fixture_bundle, export_fixture


def test_build_fixture_bundle_includes_audit_and_probe_metadata() -> None:
    html = """
    <html>
      <head>
        <meta name="generator" content="Shopify">
        <link rel="stylesheet" href="https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/base.css">
      </head>
      <body>
        <script src="https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/global.js"></script>
        <script>Shopify.theme = {"name": "Dawn"};</script>
        <button class="quick-add__submit">Add</button>
      </body>
    </html>
    """

    bundle = build_fixture_bundle(
        url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        html=html,
        asset_bodies={
            "https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/global.js": "const drawer='predictive-search';",
            "https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/base.css": ".quick-add__submit{display:block}",
        },
    )

    assert bundle["selected_asset_urls"]
    assert bundle["audit"]["assessment"]["likely_base_theme"] == "Dawn"
    assert "quick-add__submit" in bundle["raw_signals"]["asset_content_tokens"]


def test_export_fixture_writes_json_bundle(tmp_path, monkeypatch) -> None:
    response = httpx.Response(
        200,
        request=httpx.Request("GET", "https://example.com"),
        text=(
            "<html><head><meta name=\"generator\" content=\"Shopify\"></head>"
            "<body><script>Shopify.theme = {\"name\": \"Dawn\"};</script></body></html>"
        ),
    )

    monkeypatch.setattr("shopify_theme_audit.exporter.fetch_html", lambda url: response)
    monkeypatch.setattr("shopify_theme_audit.exporter.fetch_text_assets", lambda urls: {})

    output_path = tmp_path / "fixtures" / "example.json"
    written_path = export_fixture("https://example.com", output_path)
    payload = json.loads(written_path.read_text(encoding="utf-8"))

    assert written_path == output_path
    assert payload["url"] == "https://example.com"
    assert payload["audit"]["shopify_detected"] is True
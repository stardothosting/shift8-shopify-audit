from shopify_theme_audit.asset_probe import build_asset_probe_signals, select_probe_asset_urls
from shopify_theme_audit.catalog import STARTER_THEME_CATALOG, THEME_CATALOG


def test_select_probe_asset_urls_prioritizes_high_signal_assets() -> None:
    signals = {
        "script_urls": [
            "https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/runtime.js",
            "https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/global.js",
        ],
        "stylesheet_urls": [
            "https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/base.css",
            "https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/print.css",
        ],
    }

    probe_urls = select_probe_asset_urls(signals, limit=2)

    assert probe_urls == [
        "https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/global.js",
        "https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/base.css",
    ]


def test_build_asset_probe_signals_extracts_catalog_tokens() -> None:
    asset_bodies = {
        "https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/global.js": "const feature = 'quick-add__submit';",
        "https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/base.css": ".price__container { display:block; }",
    }

    signals, clues = build_asset_probe_signals(asset_bodies, (THEME_CATALOG, STARTER_THEME_CATALOG))

    assert "quick-add__submit" in signals["asset_content_tokens"]
    assert "price__container" in signals["asset_content_tokens"]
    assert len(clues) >= 2
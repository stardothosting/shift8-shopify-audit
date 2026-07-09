from shopify_theme_audit.cross_reference import analyze_asset_cross_reference


def test_cross_reference_extracts_custom_namespace_candidates() -> None:
    signals = {
        "script_urls": ["https://example.com/cdn/shop/t/1/assets/quick-add.min.js"],
        "stylesheet_urls": [
            "https://example.com/cdn/shop/t/1/assets/section-ph-header.min.css",
            "https://example.com/cdn/shop/t/1/assets/section-ph-hero-banner.min.css",
            "https://example.com/cdn/shop/t/1/assets/section-ph-text-media.min.css",
        ],
        "asset_filenames": [
            "quick-add.min.js",
            "section-ph-header.min.css",
            "section-ph-hero-banner.min.css",
            "section-ph-text-media.min.css",
        ],
        "theme_asset_ids": ["1"],
        "classes": ["ph-header", "ph-hero-banner", "ph-text-media", "ph-featured-products"],
    }

    cross_reference = analyze_asset_cross_reference(signals)

    assert cross_reference.custom_namespaces == ["ph"]
    assert cross_reference.theme_asset_ids == ["1"]
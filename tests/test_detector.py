from shopify_theme_audit.detector import assess_theme_identity, score_candidates, score_lineages
from shopify_theme_audit.models import AssetCrossReference, Evidence


def test_score_candidates_prioritizes_exact_theme_name_and_tokens() -> None:
    signals = {
        "script_urls": ["https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/ap-theme.js"],
        "stylesheet_urls": ["https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/ap-theme.css"],
        "classes": ["ap-productform", "theme--prestige"],
        "attributes": [],
        "theme_names": ["Prestige"],
        "meta": ["Shopify"],
    }
    clues = [
        Evidence(
            kind="theme_name",
            source="script_text",
            value="Prestige",
            weight=10,
            reason="Theme name exposed in storefront JavaScript.",
        )
    ]

    candidates = score_candidates(signals, clues)

    assert candidates[0].name == "Prestige"
    assert candidates[0].score >= 20


def test_assessment_marks_custom_theme_as_dawn_derived_when_signatures_match() -> None:
    signals = {
        "script_urls": ["https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/global.js"],
        "stylesheet_urls": ["https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/component-slider.css"],
        "asset_paths": ["/s/files/1/0000/1111/t/7/assets/global.js", "/s/files/1/0000/1111/t/7/assets/component-slider.css"],
        "asset_filenames": ["global.js", "component-slider.css"],
        "classes": ["price__container", "quick-add__submit"],
        "attributes": [],
        "theme_names": ["Acme Custom"],
        "meta": ["Shopify"],
    }
    clues = [
        Evidence(
            kind="theme_name",
            source="script_text",
            value="Acme Custom",
            weight=10,
            reason="Theme name exposed in storefront JavaScript.",
        )
    ]

    candidates = score_candidates(signals, clues)
    lineage, diagnostics = score_lineages(signals, clues)
    assessment = assess_theme_identity(True, clues, candidates, lineage, AssetCrossReference(asset_count=2))

    assert lineage[0].name == "Dawn"
    assert diagnostics[0].qualified is True
    assert assessment.classification == "custom-derived"
    assert assessment.likely_base_theme == "Dawn"
    assert assessment.exposed_theme_name == "Acme Custom"
    assert assessment.customness_score >= 80


def test_assessment_does_not_promote_theme_handle_noise() -> None:
    clues = []

    assessment = assess_theme_identity(True, clues, [], [], AssetCrossReference(asset_count=2))

    assert assessment.classification == "shopify-unclassified"
    assert assessment.customness_score == 55


def test_assessment_prefers_custom_namespace_over_single_generic_dawn_token() -> None:
    weak_dawn_candidate = score_candidates(
        {
            "script_urls": [],
            "stylesheet_urls": [],
            "asset_paths": [],
            "asset_filenames": [],
            "asset_content_tokens": ["predictive-search"],
            "classes": [],
            "attributes": [],
            "theme_names": [],
            "meta": [],
        },
        [],
    )
    weak_dawn_lineage, diagnostics = score_lineages(
        {
            "script_urls": [],
            "stylesheet_urls": [],
            "asset_paths": [],
            "asset_filenames": [],
            "asset_content_tokens": ["predictive-search"],
            "classes": [],
            "attributes": [],
            "theme_names": [],
            "meta": [],
        },
        [],
    )

    assessment = assess_theme_identity(
        True,
        [],
        weak_dawn_candidate,
        weak_dawn_lineage,
        AssetCrossReference(asset_count=12, custom_namespaces=["ph"]),
    )

    assert diagnostics[0].qualified is False
    assert assessment.classification == "shopify-custom"
    assert assessment.likely_base_theme is None


def test_score_lineages_uses_asset_content_tokens() -> None:
    signals = {
        "script_urls": [],
        "stylesheet_urls": [],
        "asset_paths": [],
        "asset_filenames": [],
        "asset_content_tokens": ["global.js", "component-cart-items.css", "quick-add__submit"],
        "classes": [],
        "attributes": [],
        "theme_names": ["Bespoke Theme"],
        "meta": ["Shopify"],
    }

    lineage, diagnostics = score_lineages(signals, [])

    assert lineage[0].name == "Dawn"
    assert lineage[0].score > 0
    assert diagnostics[0].qualified is True
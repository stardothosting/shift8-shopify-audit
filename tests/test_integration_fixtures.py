from __future__ import annotations

import json
from pathlib import Path

from shopify_theme_audit.detector import audit_storefront_payload
from shopify_theme_audit.library import library_entries


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_fixture_bundles_cover_known_and_custom_lineage_paths() -> None:
    fixture_files = (
        "dawn_reference.json",
        "custom_dawn_derivative.json",
        "prestige_direct.json",
    )

    for fixture_name in fixture_files:
        payload = json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))
        audit = audit_storefront_payload(
            url=payload["url"],
            final_url=payload["final_url"],
            status_code=payload["status_code"],
            html=payload["html"],
            asset_bodies=payload["asset_bodies"],
        )

        assert audit.assessment.classification == payload["expected"]["classification"]
        assert audit.assessment.likely_base_theme == payload["expected"]["likely_base_theme"]


def test_library_registry_contains_priority_families() -> None:
    slugs = {entry.slug for entry in library_entries()}

    assert "dawn-reference" in slugs
    assert "shopify-free-themes" in slugs
    assert "legacy-vintage-shopify" in slugs
    assert "commercial-priority-seeds" in slugs
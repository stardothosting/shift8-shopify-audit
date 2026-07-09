from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LibraryEntry:
    slug: str
    family: str
    role: str
    source: str
    confidence: str
    theme_names: tuple[str, ...]
    notes: str


THEME_LIBRARY: tuple[LibraryEntry, ...] = (
    LibraryEntry(
        slug="dawn-reference",
        family="starter-theme",
        role="reference",
        source="official",
        confidence="verified",
        theme_names=("Dawn",),
        notes="Shopify's source-available reference theme and the highest-priority lineage base for Online Store 2.0 custom themes.",
    ),
    LibraryEntry(
        slug="shopify-free-themes",
        family="shopify-authored",
        role="priority-audit-cluster",
        source="official-theme-store",
        confidence="verified-membership",
        theme_names=("Spotlight", "Sense", "Atelier", "Savor", "Horizon"),
        notes="Current free themes visible in the official Theme Store listing. These are high-value audit targets because merchants often start from free Shopify themes before customizing.",
    ),
    LibraryEntry(
        slug="legacy-vintage-shopify",
        family="legacy-shopify",
        role="priority-lineage-cluster",
        source="historical",
        confidence="research-needed",
        theme_names=("Debut", "Brooklyn", "Boundless", "Supply", "Venture", "Simple", "Narrative"),
        notes="Common legacy Shopify theme family worth supporting for older storefronts and migration-era custom builds. Fixture capture should confirm exact signatures before scoring rules are promoted.",
    ),
    LibraryEntry(
        slug="commercial-priority-seeds",
        family="commercial",
        role="priority-audit-cluster",
        source="theme-store-observed",
        confidence="seed-only",
        theme_names=("Prestige", "Impulse", "Warehouse", "Turbo"),
        notes="High-value commercial seed themes to calibrate with licensed storefront fixtures. Keep evidence fixture-backed because code access is limited.",
    ),
)


def library_entries() -> tuple[LibraryEntry, ...]:
    return THEME_LIBRARY
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Evidence:
    kind: str
    source: str
    value: str
    weight: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CandidateTheme:
    name: str
    score: int
    matched_evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["matched_evidence"] = [item.to_dict() for item in self.matched_evidence]
        return data


@dataclass(slots=True)
class ThemeAssessment:
    classification: str
    confidence: int
    customness_score: int = 0
    exposed_theme_name: str | None = None
    likely_base_theme: str | None = None
    rationale: str = ""
    matched_evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["matched_evidence"] = [item.to_dict() for item in self.matched_evidence]
        return data


@dataclass(slots=True)
class AssetCrossReference:
    asset_count: int
    shared_filename_stems: list[str] = field(default_factory=list)
    shared_filename_prefixes: list[str] = field(default_factory=list)
    filename_tokens: list[str] = field(default_factory=list)
    custom_namespaces: list[str] = field(default_factory=list)
    theme_asset_ids: list[str] = field(default_factory=list)
    shopify_cloud_assets: list[str] = field(default_factory=list)
    extension_assets: list[str] = field(default_factory=list)
    app_assets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LineageDiagnostic:
    theme_name: str
    strong_matches: list[str] = field(default_factory=list)
    weak_matches: list[str] = field(default_factory=list)
    qualified: bool = False
    score: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StorefrontAudit:
    url: str
    final_url: str
    status_code: int
    shopify_detected: bool
    clues: list[Evidence]
    candidate_themes: list[CandidateTheme]
    lineage_themes: list[CandidateTheme]
    lineage_diagnostics: list[LineageDiagnostic]
    assessment: ThemeAssessment
    raw_signals: dict[str, list[str]]
    asset_cross_reference: AssetCrossReference = field(default_factory=lambda: AssetCrossReference(asset_count=0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "status_code": self.status_code,
            "shopify_detected": self.shopify_detected,
            "clues": [clue.to_dict() for clue in self.clues],
            "candidate_themes": [theme.to_dict() for theme in self.candidate_themes],
            "lineage_themes": [theme.to_dict() for theme in self.lineage_themes],
            "lineage_diagnostics": [item.to_dict() for item in self.lineage_diagnostics],
            "assessment": self.assessment.to_dict(),
            "asset_cross_reference": self.asset_cross_reference.to_dict(),
            "raw_signals": self.raw_signals,
        }


@dataclass(slots=True)
class ProviderConfig:
    name: str
    api_key: str
    model: str
    base_url: str


@dataclass(slots=True)
class AppConfig:
    providers: dict[str, ProviderConfig]

    def get_provider(self, provider_name: str) -> ProviderConfig:
        try:
            return self.providers[provider_name]
        except KeyError as exc:
            raise KeyError(f"Provider '{provider_name}' is not configured.") from exc
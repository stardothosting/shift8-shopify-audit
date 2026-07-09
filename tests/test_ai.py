import httpx

from shopify_theme_audit.ai import summarize_audit
from shopify_theme_audit.models import Evidence, ProviderConfig, StorefrontAudit, ThemeAssessment


def test_summarize_audit_uses_openai_compatible_chat_api(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = request.read().decode("utf-8")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Likely Prestige."}}]},
        )

    transport = httpx.MockTransport(handler)

    class MockClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("shopify_theme_audit.ai.httpx.Client", MockClient)
    provider = ProviderConfig(
        name="openai",
        api_key="secret",
        model="gpt-4.1-mini",
        base_url="https://api.openai.com/v1",
    )
    audit = StorefrontAudit(
        url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        shopify_detected=True,
        clues=[
            Evidence(
                kind="theme_name",
                source="script_text",
                value="Prestige",
                weight=10,
                reason="Theme name exposed in storefront JavaScript.",
            )
        ],
        candidate_themes=[],
        lineage_themes=[],
        lineage_diagnostics=[],
        assessment=ThemeAssessment(
            classification="known-theme",
            confidence=90,
            exposed_theme_name="Prestige",
            likely_base_theme="Prestige",
            rationale="The storefront exposes a matching known theme name.",
        ),
        raw_signals={},
    )

    summary = summarize_audit(audit, provider)

    assert summary == "Likely Prestige."
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["authorization"] == "Bearer secret"
    assert '"model":"gpt-4.1-mini"' in str(captured["payload"])
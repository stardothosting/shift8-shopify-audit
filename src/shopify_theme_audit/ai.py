from __future__ import annotations

import json

import httpx

from .models import ProviderConfig, StorefrontAudit


class AIError(RuntimeError):
    """Raised when AI summarization fails."""


def summarize_audit(audit: StorefrontAudit, provider: ProviderConfig, timeout: float = 30.0) -> str:
    payload = {
        "model": provider.model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Shopify theme forensic analyst. "
                    "Review the structured storefront evidence, rank likely theme candidates, "
                    "and explain confidence plus contradictory clues."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Summarize this storefront audit. Focus on likely theme identity, alternate candidates, "
                    "and the strongest evidence.\n\n"
                    + json.dumps(audit.to_dict(), indent=2)
                ),
            },
        ],
    }
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(f"{provider.base_url}/chat/completions", json=payload, headers=headers)
        response.raise_for_status()

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise AIError("Unexpected AI response format.") from exc
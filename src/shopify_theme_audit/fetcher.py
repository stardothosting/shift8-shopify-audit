from __future__ import annotations

import httpx


USER_AGENT = "shopify-theme-audit/0.1 (+https://example.invalid)"


def fetch_html(url: str, timeout: float = 20.0) -> httpx.Response:
    with _build_client(timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        return response


def fetch_text_assets(urls: list[str], timeout: float = 10.0, max_bytes: int = 250_000) -> dict[str, str]:
    assets: dict[str, str] = {}
    if not urls:
        return assets

    with _build_client(timeout=timeout) as client:
        for url in urls:
            response = client.get(url)
            if response.status_code >= 400:
                continue
            content_type = response.headers.get("Content-Type", "")
            if "javascript" not in content_type and "css" not in content_type and "text" not in content_type:
                continue
            assets[url] = response.text[:max_bytes]
    return assets


def _build_client(timeout: float) -> httpx.Client:
    return httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
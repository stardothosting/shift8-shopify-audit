from shopify_theme_audit.fingerprints import extract_signals


def test_extract_signals_finds_shopify_and_theme_name() -> None:
    html = """
    <html>
      <head>
        <meta name="generator" content="Shopify">
        <link rel="stylesheet" href="https://cdn.shopify.com/s/files/1/0000/1111/t/7/assets/ap-theme.css">
      </head>
      <body class="template-product theme--prestige">
        <script>
          Shopify.theme = {"name": "Prestige"};
        </script>
      </body>
    </html>
    """

    signals, clues, shopify_detected = extract_signals(html, "https://example.com")

    assert shopify_detected is True
    assert "Prestige" in signals["theme_names"]
    assert "ap-theme.css" in signals["asset_filenames"]
    assert any(clue.kind == "theme_name" and clue.value == "Prestige" for clue in clues)
    assert any(clue.kind == "platform" and "cdn.shopify.com" in clue.value for clue in clues)
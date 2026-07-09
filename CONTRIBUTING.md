# Contributing

## Scope

This project audits public Shopify storefront evidence to identify likely theme matches, starter-theme lineage, and custom-theme signals.

Contributions are most useful when they improve one of these areas:

- signal extraction from public storefront markup and assets
- deterministic scoring and assessment quality
- fixture capture and regression coverage
- documentation for repeatable research workflows

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python3 -m pytest tests
```

## Contribution guidelines

- Keep the deterministic audit path working without AI providers.
- Prefer small, reviewable changes over broad rewrites.
- Add or update tests with every scoring or extraction change.
- Use fixture-backed evidence for new signatures whenever possible.
- Do not commit API keys, local config files, or raw secrets.

## Signature changes

When adding new theme or lineage signatures:

1. Capture a fixture bundle from a real storefront.
2. Reduce it to the smallest evidence set that still reproduces the result.
3. Add or update tests that show why the new signature matters.
4. Record whether the signature is verified, suspected, or seed-only.

## Pull requests

- Explain the storefront or theme family the change targets.
- Note any new fixture bundles and why they are representative.
- Include the test command and outcome.

## Security

If the change affects secrets, provider configuration, or data capture behavior, review [SECURITY.md](SECURITY.md) before opening the pull request.
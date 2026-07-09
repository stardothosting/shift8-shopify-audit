# Shopify Theme Audit

`shopify-theme-audit` is a Python CLI for identifying Shopify themes from storefront evidence.

The tool starts with deterministic signals from HTML, asset URLs, and DOM structure. It can then probe a small set of high-signal CSS and JavaScript assets to improve theme and lineage detection. AI summarization is optional and sits on top of the raw audit output rather than replacing it.

## Current scope

- Detect Shopify storefront indicators from public HTML and assets.
- Score direct theme matches from a signature catalog.
- Estimate starter-theme lineage for custom builds, with Dawn as the first verified base.
- Probe selected CSS and JavaScript assets for hidden signature tokens.
- Export structured results that can be reviewed directly or summarized by an OpenAI-compatible provider.

## Architecture

The audit flow is intentionally layered:

1. Fetch storefront HTML.
2. Extract raw signals from markup, asset URLs, and exposed theme data.
3. Probe a short list of high-signal assets when Shopify is detected.
4. Score known themes and starter-theme lineage from combined signals.
5. Produce a theme assessment with confidence, likely base theme, and customness score.
6. Optionally send the structured audit to an LLM for a second-pass summary.

AI is not part of the scoring path. The core audit is deterministic and testable without external providers.

## Signature library

The project keeps separate buckets for different kinds of evidence:

- Known theme signatures for direct matches.
- Starter-theme signatures for lineage matches.
- Fixture bundles for regression tests against stored storefront samples.
- A library registry for priority families and research status.

At this stage, Dawn is the only verified source-available reference base. The library also tracks Shopify-authored free themes, legacy Shopify families, and commercial seed themes that should only be promoted after fixture-backed validation.

## Security model

Provider keys are not stored in the repository.

Default config path:

```text
~/.config/shopify-theme-audit/config.toml
```

The CLI writes this file with `0600` permissions and rejects group- or world-readable configs.

The preferred setup is to keep API keys in environment variables and reference them from the config file:

```toml
[providers.openai]
api_key = "env:OPENAI_API_KEY"
model = "gpt-4.1-mini"
base_url = "https://api.openai.com/v1"

[providers.deepseek]
api_key = "env:DEEPSEEK_API_KEY"
model = "deepseek-chat"
base_url = "https://api.deepseek.com/v1"
```

That keeps secrets out of source control and out of project-local configuration.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
shopify-theme-audit init-config
export OPENAI_API_KEY="..."
export DEEPSEEK_API_KEY="..."
```

## Usage

```bash
shopify-theme-audit audit https://example-shop.myshopify.com
shopify-theme-audit audit https://example.com --format json
shopify-theme-audit audit https://example.com --with-ai --provider deepseek
shopify-theme-audit init-config
shopify-theme-audit export-fixture https://example.com --output tests/fixtures/example.json
```

## Building the fixture library

The fixture workflow is meant to make signature research reproducible.

Use `export-fixture` to capture a storefront into a normalized bundle with:

- the fetched HTML
- the selected asset probe URLs
- the fetched CSS and JavaScript asset bodies
- the raw extracted signals
- the current audit result

Example:

```bash
shopify-theme-audit export-fixture https://example.com --output tests/fixtures/example.json
```

That bundle can then be reviewed, trimmed if needed, and promoted into a regression fixture once its expected classification is known.

## Development

Run the test suite with:

```bash
python3 -m pytest tests
```

The current test coverage includes:

- raw signal extraction
- known-theme scoring
- lineage scoring
- asset-probe selection and token extraction
- config validation and secret resolution
- AI request shaping
- fixture-backed integration checks

## Project docs

- contribution guide: `CONTRIBUTING.md`
- security policy: `SECURITY.md`
- license: `LICENSE.md`

## Repository layout

```text
src/shopify_theme_audit/
tests/
tests/fixtures/
```

Key modules:

- `detector.py`: audit flow and scoring
- `fingerprints.py`: HTML and DOM signal extraction
- `asset_probe.py`: second-stage asset selection and token extraction
- `catalog.py`: direct-match and lineage signature catalogs
- `library.py`: priority theme families and research registry
- `config.py`: secure provider configuration loading

## Best-practice notes

The current baseline is sound for an early open-source CLI:

- secrets stay outside the repo by default
- config permissions are enforced
- the audit core is deterministic
- AI is optional and isolated
- fixture-backed tests protect the scoring model

There is still room to harden the project further as it grows. Useful follow-up work includes retry and backoff policy for network fetches, optional redaction for persisted audit bundles, richer fixture capture tooling, and clearer contribution guidance for signature additions.

## Roadmap

- grow the fixture library from real storefront captures
- expand verified starter-theme and legacy-theme lineage coverage
- add a CLI workflow for exporting normalized fixture bundles
- add release documentation once the public API stabilizes
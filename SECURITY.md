# Security Policy

## Supported scope

This project processes public storefront data and optional AI-provider credentials supplied by the user.

The current security priorities are:

- keeping provider credentials out of the repository
- limiting fixture exports to intended storefront evidence
- keeping the deterministic audit path independent from AI providers

## Secrets handling

- Store provider configuration outside the repository.
- Prefer environment-variable references such as `env:OPENAI_API_KEY` and `env:DEEPSEEK_API_KEY`.
- Do not commit local config files, `.env` files, or exported secrets.
- Keep `~/.config/shopify-theme-audit/config.toml` readable only by the local user.

## Reporting a vulnerability

If you find a security issue, do not open a public issue with exploit details.

Report it privately with:

- a short description of the issue
- the affected component or command
- reproduction steps if available
- the expected and actual behavior

Until a dedicated security contact is published, use the repository owner's private contact path and avoid disclosing active secrets in the report.

## Operational notes

- Review exported fixture bundles before committing them.
- Treat local Git remotes with embedded credentials as sensitive and remove tokens from stored remote URLs.
- Prefer tokenless HTTPS remotes, a credential helper, or SSH for Git authentication.
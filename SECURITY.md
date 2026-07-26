# Security Policy

## Supported Versions

This project is maintained from the default branch. Security fixes are made there first.

## Reporting a Vulnerability

Please do not open a public issue for credential leaks, account-access bugs, or unsafe browser automation behavior.

Use GitHub private vulnerability reporting if it is enabled for the repository, or contact a maintainer privately. Include:

- A clear description of the issue.
- Steps to reproduce, if safe to share.
- Whether credentials, cookies, browser profiles, screenshots, or exported HTML may have been exposed.
- Any suggested fix or mitigation.

Maintainers should acknowledge valid reports as soon as practical and avoid sharing sensitive details publicly until a fix or mitigation is available.

## Sensitive Data

This project reads credentials from `.env` and stores a local browser profile in `.auth/`. Both are ignored by Git and must never be committed.

Before publishing or sharing a fork, check for:

- Real `.env` files or credential-like values in examples.
- `.auth/` browser profiles.
- `discovery_output/` screenshots or HTML from authenticated pages.
- Logs that include account identifiers, cookies, tokens, or personal data.

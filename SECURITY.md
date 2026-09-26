# Security policy

RESIDUAL is under active research and development.

## Reporting a vulnerability

Do not publish exploit details, credentials, tokens, private keys, customer data or other sensitive material in a public issue.

Prefer GitHub's private vulnerability reporting / Security Advisory workflow when available. If private reporting is unavailable, open a minimal public issue requesting a private security contact without including exploitation details.

## Scope

Reports involving the Apache-2.0 Open Core, release pipeline, authentication/authorization boundaries, sandboxing, evidence integrity, supply-chain handling or secret exposure are in scope.

Commercial/enterprise components may use a separate disclosure process when distributed.

## Claims

A passing automated test or verifier is evidence only for its encoded conditions. It must not be represented as a universal security guarantee.

## Secrets

Never commit production credentials, API keys, private certificates, employer secrets or customer secrets. Rotate any credential suspected of exposure rather than relying on deletion from Git history.

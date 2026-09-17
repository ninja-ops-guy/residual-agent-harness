# Provider Production-Gate Hardening

## Purpose
Prevent recurrence of the provider COI regression by adding evidence at the layer the old tests skipped.

## Enforcement
- Keep `/demo/` isolated and `/provider/` non-isolated.
- Add `provider_sdk_smoke.py`, which loads the real Puter SDK from the published Pages origin after deployment.
- Run the real-SDK check in desktop and narrow Chromium after the existing published WebVM checks.
- Do not authenticate, enumerate models, or invoke inference in this CI gate.
- Keep deterministic provider fixtures for protocol/auth/error-path behavior.
- Pin guardrail expectations in tests and repository-level agent instructions.

## Documentation
Adds release guardrails, acceptance-layer taxonomy, service-worker boundary map, test matrix, do-not-merge conditions, qualification ordering, triage, incident postmortem, and agent review templates.

## Claim boundary
This hardening does not claim real Puter authentication/inference or physical iOS/WebKit qualification. Those remain separately evidenced layers.

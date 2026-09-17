# RESIDUAL Agent Instructions

These repository instructions supplement task-specific specs. Preserve RESIDUAL's fail-closed trust boundaries and retained evidence.

## Demo / provider / Pages work

Before modifying `site/**`, `demo/**`, Pages workflows, service workers, provider transport, browser acceptance, or release behavior, read `docs/release/DEMO_REGRESSION_GUARDRAILS.md`.

Required invariants:

- `/demo/` remains cross-origin isolated for WebVM.
- `/provider/` remains outside the WebVM COOP/COEP response-rewrite boundary.
- Never globally disable COOP/COEP to repair provider loading.
- Deterministic provider fixtures do not prove that the real external SDK loads.
- Pages production acceptance must bind the public artifact to the exact merged SHA.
- Published provider acceptance must load the real Puter SDK from `js.puter.com` without signing in or invoking inference.
- Real provider inference, when claimed, requires separate retained real-account evidence.
- Narrow Chromium is not physical iOS/WebKit qualification.
- Retain the first production failure. Do not rerun unchanged code solely to obtain green evidence.

When reporting a regression, classify the failing layer: artifact identity, WebVM isolation, provider isolation, provider SDK load, provider authentication, provider protocol, provider inference, or device runtime. Do not collapse distinct layers into a generic provider/demo status.

## Merge discipline

A green unit test is not sufficient evidence for browser-origin, third-party resource, service-worker, or physical-device behavior. For release-affecting changes, require the appropriate generated-artifact proof and first post-merge published-origin proof. If an applicable layer was not exercised, label it NOT_RUN/UNKNOWN rather than PASS.

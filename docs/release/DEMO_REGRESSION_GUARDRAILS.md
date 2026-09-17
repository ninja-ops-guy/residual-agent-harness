# Demo and Provider Regression Guardrails

Status: release-critical policy

This document exists because a production regression passed automated browser qualification while the public provider helper could no longer load the real Puter SDK. The root cause was a boundary mismatch: the root COI service worker applied WebVM COOP/COEP response headers to `/provider/`, and test-double provider coverage did not exercise the external SDK request.

## Non-negotiable architecture boundaries

- `/demo/` is the heavyweight WebVM execution surface and MUST remain cross-origin isolated.
- `/provider/` is the optional browser provider helper and MUST remain outside the WebVM COOP/COEP response-rewrite boundary so approved third-party provider SDKs can load normally.
- Provider authentication and provider inference are separate gates. Loading the SDK MUST NOT authenticate, list models, or invoke inference.
- RESIDUAL verifier/receipt authority remains authoritative. Provider connectivity never implies candidate acceptance.
- Narrow Chromium is responsive-layout/browser coverage. It MUST NOT be described as physical iPhone/WebKit qualification.

## Required release evidence

A Pages deployment is not qualified merely because the artifact built or a mocked provider passed. Production acceptance MUST prove all applicable layers:

1. Exact deployed revision: `/demo/build-info.json` and served artifact hashes bind the public page to the expected commit SHA.
2. WebVM: guest boot, shell readiness, `demo`, `verify-demo`, warm reload, Mission Control/workbench and desktop+narrow behavior pass against the published origin.
3. Provider helper isolation: `/provider/` reports `crossOriginIsolated === false`; `/demo/` remains isolated.
4. Real SDK transport: from the published `/provider/`, a user-gesture-equivalent click on `Load Puter` successfully loads `https://js.puter.com/v2/`; CORP/COEP/CSP/network failures fail the deployment gate.
5. No hidden provider action: the SDK-load gate does not sign in, enumerate models, or perform inference.
6. Real provider inference is a separate retained acceptance when claimed. Test doubles MUST be labeled test-double coverage and never substituted for real-provider evidence.
7. Physical iOS/WebKit is a separate device gate whenever the release claims that path.

## Agent rules before changing demo, Pages, service workers, provider, or deployment code

Agents MUST inspect interactions across `site/coi-serviceworker.js`, `.github/workflows/pages.yml`, `demo/vm/provider.html`, `demo/vm/provider.js`, `demo/vm/provider-session.js`, `demo/vm/browser_smoke.py`, `demo/vm/provider_failure_smoke.py`, `demo/vm/provider_sdk_smoke.py`, and publication tests before proposing a merge.

Do not reason about one file in isolation when a change affects origin policy, service-worker scope, provider loading, navigation, caching, or deployment. Explicitly map which paths are controlled by each service worker and which response headers each path receives.

Do not replace a real external-resource acceptance with a route-fulfilled fixture. Fixtures are appropriate for deterministic protocol/error-path testing, but they cannot prove that the production browser may load the real SDK.

Do not weaken `/demo/` isolation to make `/provider/` work. Exempt only the smallest same-origin helper path required. Any broader COOP/COEP bypass is a release blocker until separately justified and qualified.

Do not call narrow Chromium "mobile acceptance" without qualification. Use "narrow Chromium" unless a physical/mobile-engine test actually ran. Physical Safari/WebKit failures remain authoritative even if narrow Chromium is green.

Do not merge a Pages-affecting change based only on PR artifact proof. The first production deployment of the merged SHA is authoritative for public-origin behavior. Retain its first failure; do not rerun unchanged code merely to manufacture green evidence.

## Regression taxonomy

Keep these outcomes distinct in reports and PR descriptions:

- `ARTIFACT_IDENTITY`: wrong/stale deployed SHA or artifact hash.
- `WEBVM_ISOLATION`: `/demo/` lost required cross-origin isolation.
- `PROVIDER_ISOLATION`: `/provider/` incorrectly inherited WebVM isolation.
- `PROVIDER_SDK_LOAD`: real Puter SDK could not initialize from the public origin.
- `PROVIDER_AUTH`: authentication/sign-in failed after SDK load.
- `PROVIDER_PROTOCOL`: model response crossed transport but violated the RESIDUAL envelope.
- `PROVIDER_INFERENCE`: real provider/model request failed or succeeded.
- `DEVICE_RUNTIME`: physical browser/runtime behavior such as iOS WebKit process termination.

Never collapse these into a generic "demo failed" or "provider failed" when evidence can identify the layer.

## Merge checklist

Before merging a release-affecting PR, the agent must be able to answer yes to each applicable question: Is the exact head known? Are demo/provider service-worker scopes understood? Does deterministic fixture coverage pass? Does generated desktop+narrow browser proof pass? Does the change preserve `/demo/` isolation? Does `/provider/` remain non-isolated? After merge, did the first production deployment bind to the merged SHA? Did published desktop+narrow WebVM acceptance pass? Did the published provider helper load the real Puter SDK without authentication or inference? If physical iOS/WebKit is claimed, was it actually tested on that class of device/runtime? If real provider inference is claimed, is retained real-account evidence present?

If any required answer is unknown, report UNKNOWN/BLOCKED rather than inferring success from adjacent green tests.

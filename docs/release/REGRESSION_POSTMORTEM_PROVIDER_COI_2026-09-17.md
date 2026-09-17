# Provider COI Regression — 2026-09-17

## Symptom

The public Mission Control demo could open provider setup, but `Load Puter` failed. Browser evidence showed the external Puter SDK request rejected under cross-origin resource policy.

## Root cause

The root GitHub Pages COI service worker controlled the same-origin `/provider/` helper and injected the WebVM COOP/COEP response headers there. Those headers are required for `/demo/` WebVM, but the provider helper must load an external browser SDK and therefore cannot inherit that response-rewrite boundary.

## Why existing gates missed it

Existing provider browser acceptance routed `https://js.puter.com/v2/**` to a deterministic local fixture. That was correct for repeatable provider protocol and failure-path testing, but it bypassed the network/browser-policy layer that failed in production. Narrow Chromium also represented viewport/browser acceptance, not physical iOS/WebKit qualification.

## Corrective actions

- Scope the COI service-worker bypass narrowly to same-origin `/provider/` while preserving `/demo/` isolation.
- Keep deterministic provider fixtures for protocol/error-path coverage.
- Add a separate post-deploy gate that clicks `Load Puter` on the published `/provider/` and requires the real `js.puter.com/v2/` SDK to initialize.
- The real-SDK gate performs no authentication, model enumeration, or inference.
- Bind public demo acceptance to the exact merged SHA and retain first production failure evidence.
- Document explicit acceptance-layer taxonomy and agent instructions.

## Prevention rule

Any future service-worker, COOP/COEP, provider, Pages, navigation, or caching change must be evaluated across both `/demo/` and `/provider/`. A test-double provider PASS can never be used as evidence that the external SDK is loadable from the production origin.

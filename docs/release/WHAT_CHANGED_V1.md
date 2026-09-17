# What Changed in Regression Gate v1

- Added a published-origin real Puter SDK initialization smoke test.
- Wired it into post-deploy Pages qualification for desktop and narrow Chromium.
- Added source tests preventing accidental removal or conversion into an auth/inference test.
- Added repository-level `AGENTS.md` instructions.
- Documented `/demo/` vs `/provider/` service-worker/isolation boundaries.
- Defined independent acceptance layers and evidence naming.
- Added do-not-merge conditions, qualification order, triage, review templates, and incident postmortem.
- Explicitly separated narrow Chromium from physical iOS/WebKit and SDK load from real provider inference.
